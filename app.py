import os
import io
import csv
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, url_for

# Get the absolute path to the directory where this app.py file is located
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Define file paths relative to this BASE_DIR
NUTRITION_PREP_FILE = os.path.join(BASE_DIR, 'nutrition_prep_data.csv')
STORAGE_INSTRUCTION_FILENAME = os.path.join(BASE_DIR, 'storage_instruction.txt')

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'), static_folder=os.path.join(BASE_DIR, 'static'))

# --- Helper Function to Load Nutrition and Preparation Data ---
def load_nutrition_prep_data():
    data = {}
    expected_headers_for_new_file = ['Product', 'Variant', 'Calories', 'Protein', 'Carbs', 'Fat', 'How to Prepare']
    try:
        with open(NUTRITION_PREP_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                print(f"Warning: {NUTRITION_PREP_FILE} is empty or not a valid CSV. No macro data loaded.")
                return data
            for row in reader:
                product = row.get('Product', '').strip().lower()
                variant = row.get('Variant', '').strip().lower()
                key = (product, variant)
                data[key] = {
                    'Product': row.get('Product', ''),
                    'Variant': row.get('Variant', ''),
                    'Calories': row.get('Calories', ''),
                    'Protein': row.get('Protein', ''),
                    'Carbs': row.get('Carbs', ''),
                    'Fat': row.get('Fat', ''),
                    'How to Prepare': row.get('How to Prepare', '')
                }
                if 'Expiry Days' in row: # Still load if present for backward compatibility in this load function
                     data[key]['Expiry Days'] = row.get('Expiry Days', '')

    except FileNotFoundError:
        print(f"Info: {NUTRITION_PREP_FILE} not found. It can be created via the editor.")
        print(f"Expected headers for new file via editor: {', '.join(expected_headers_for_new_file)}")
    except Exception as e:
        print(f"Error reading {NUTRITION_PREP_FILE}: {e}")
    return data

# Initialize nutrition_prep_data when the app starts
nutrition_prep_data = load_nutrition_prep_data()

# --- Route for the main page (label generator) ---
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# --- Route to process the uploaded CSV for label generation ---
@app.route('/process_csv', methods=['POST'])
def process_csv():
    global nutrition_prep_data
    nutrition_prep_data = load_nutrition_prep_data() # Reload data in case it was edited

    if 'csv_file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['csv_file']
    if not file or file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and file.filename.endswith('.csv'):
        try:
            file.stream.seek(0)
            content_bytes = file.read()
            try:
                content_string = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                return jsonify({'error': 'Error decoding CSV file. Please ensure it is UTF-8 encoded.'}), 400

            csv_file_like_object = io.StringIO(content_string)
            reader = csv.DictReader(csv_file_like_object)

            if not reader.fieldnames:
                return jsonify({'error': 'CSV file is empty or does not contain headers.'}), 400

            labels_data = []
            missing_macros_log = [] # To store logs for missing macros
            generation_date = datetime.now().date()
            # MODIFICATION: Change date format for generation_date_str
            generation_date_str = generation_date.strftime('%m/%d/%y') # Changed from '%Y-%m-%d'

            default_expiry_days = 11 # Define default days, used in timedelta and message
            default_expiry_date = generation_date + timedelta(days=default_expiry_days)

            storage_instruction = ""
            try:
                with open(STORAGE_INSTRUCTION_FILENAME, 'r', encoding='utf-8') as f_storage:
                    custom_storage_instruction = f_storage.read().strip()
                    if custom_storage_instruction:
                        storage_instruction = custom_storage_instruction
            except FileNotFoundError:
                print(f"Info: '{STORAGE_INSTRUCTION_FILENAME}' not found. Storage instruction will be empty.")
            except Exception as e_storage:
                print(f"Error reading '{STORAGE_INSTRUCTION_FILENAME}': {e_storage}. Storage instruction will be empty.")

            selected_branding = request.form.get('branding')
            logo_url = None
            if selected_branding == 'beast_coast':
                logo_url = url_for('static', filename='beast_coast_logo.png')
            # Add other elif for other branding options as needed

            processed_rows = 0
            for row_number, row in enumerate(reader, 1):
                processed_rows +=1
                try:
                    quantity_str = row.get('Quantity', '1').strip()
                    quantity = int(float(quantity_str)) if quantity_str else 1

                    price_str = row.get('Price', '0').replace('$', '').strip()
                    price = float(price_str) if price_str else 0.0
                    price_per_item = price / quantity if quantity else 0.0

                    modifiers = row.get('Modifiers', '').strip()
                    if modifiers.lower() == 'nan':
                        modifiers = ''
                    else:
                        modifiers = modifiers.replace('(1x)', '').replace('(2x)', '').strip()

                    product_name_original = row.get('Product', '').strip()
                    variant_name_original = row.get('Variant', '').strip()

                    if not product_name_original:
                        print(f"Warning: Skipping row {row_number} due to missing 'Product' name.")
                        continue

                    product_lookup = product_name_original.lower()
                    variant_lookup = variant_name_original.lower()

                    lookup_key = (product_lookup, variant_lookup)
                    nutrition_info = nutrition_prep_data.get(lookup_key) # Get data

                    if not nutrition_info:
                        missing_macros_log.append({
                            "product": product_name_original,
                            "variant": variant_name_original
                        })
                        nutrition_info = {} # Use empty dict to avoid errors later, label will show blank nutrition

                    # MODIFICATION: Change default expiry date format
                    current_expiry_date_str = default_expiry_date.strftime('%m/%d/%y') # Changed from '%Y-%m-%d'

                    custom_expiry_days_str = nutrition_info.get('Expiry Days', '').strip()
                    if custom_expiry_days_str:
                        try:
                            custom_expiry_days = int(custom_expiry_days_str)
                            custom_expiry_date = generation_date + timedelta(days=custom_expiry_days)
                            # MODIFICATION: Change custom expiry date format
                            current_expiry_date_str = custom_expiry_date.strftime('%m/%d/%y') # Changed from '%Y-%m-%d'
                        except ValueError:
                            # MODIFICATION: Updated warning message
                            print(f"Warning: Invalid 'Expiry Days' value '{custom_expiry_days_str}' for {product_name_original} - {variant_name_original}. Using default expiry ({default_expiry_days} days).")
                            # current_expiry_date_str will remain the default formatted one set above

                    customer_full_name = row.get('Customer', '').strip()
                    customer_parts = customer_full_name.split(' ', 1)
                    customer_first_name = customer_parts[0]
                    customer_last_name = customer_parts[1] if len(customer_parts) > 1 else ''

                    for _ in range(quantity):
                        label_data = {
                            'generation_date': generation_date_str, # Already updated format
                            'logo_url': logo_url,
                            'customer_first_name': customer_first_name,
                            'customer_last_name': customer_last_name,
                            'product': product_name_original,
                            'variant': variant_name_original,
                            'modifiers': modifiers,
                            'price': f'{price_per_item:.2f}' if price_per_item else '',
                            'expiry_date': current_expiry_date_str, # Already updated format
                            'calories': nutrition_info.get('Calories', ''),
                            'protein': nutrition_info.get('Protein', ''),
                            'carbs': nutrition_info.get('Carbs', ''),
                            'fat': nutrition_info.get('Fat', ''),
                            'preparation': nutrition_info.get('How to Prepare', '')
                        }
                        labels_data.append(label_data)
                except ValueError as e:
                    return jsonify({'error': f'Error processing row {row_number} (ValueError in data: {row}). Details: {e}. Please check data types (e.g., Quantity, Price).'}), 400
                except Exception as e:
                    return jsonify({'error': f'Unexpected error processing row {row_number} ({row}). Details: {e}'}), 400

            if not processed_rows and reader.fieldnames:
                return jsonify({'error': 'CSV file contains headers but no data rows, or all rows were skipped.'}), 400
            if not labels_data and not processed_rows and not missing_macros_log:
                 return jsonify({'error': 'No valid data rows found in CSV to generate labels.'}), 400

            return jsonify({
                'labels': labels_data,
                'storage': storage_instruction,
                'missing_macros': missing_macros_log
            })

        except csv.Error as e:
             return jsonify({'error': f'Error parsing CSV structure: {e}. Please check CSV format.'}), 400
        except Exception as e:
            print(f"Unhandled error in /process_csv: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'An unexpected error occurred: {e}'}), 500

    return jsonify({'error': 'Invalid file format. Only CSV files are allowed.'}), 400

# --- Route for displaying and editing nutrition data ---
@app.route('/edit_data_page', methods=['GET'])
def edit_data_page():
    data_rows = []
    fieldnames = ['Product', 'Variant', 'Calories', 'Protein', 'Carbs', 'Fat', 'How to Prepare']
    error_message = None

    try:
        with open(NUTRITION_PREP_FILE, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            actual_fieldnames_from_csv = reader.fieldnames if reader.fieldnames else []
            for row in reader:
                row_to_add = {field: row.get(field, '') for field in fieldnames}
                data_rows.append(row_to_add)

        if not data_rows and not os.path.exists(NUTRITION_PREP_FILE):
             error_message = f"{os.path.basename(NUTRITION_PREP_FILE)} not found. Add products and save to create it."
        elif not data_rows and actual_fieldnames_from_csv:
             pass
        elif not actual_fieldnames_from_csv and os.path.exists(NUTRITION_PREP_FILE):
            error_message = f"Could not read headers from {os.path.basename(NUTRITION_PREP_FILE)}. File might be empty or corrupted."

    except FileNotFoundError:
        error_message = f"{os.path.basename(NUTRITION_PREP_FILE)} not found. Add products and save to create it."
    except Exception as e:
        error_message = f"Error reading data from {os.path.basename(NUTRITION_PREP_FILE)}: {e}"
        print(f"Error in /edit_data_page: {e}")

    return render_template('edit_data.html', headers=fieldnames, data=data_rows, error_message=error_message)

# --- Route for saving nutrition data from the editor ---
@app.route('/save_data', methods=['POST'])
def save_data():
    try:
        data_to_save = request.get_json()

        if not isinstance(data_to_save, list):
            return jsonify({'status': 'error', 'message': 'Invalid data format.'}), 400

        fieldnames = ['Product', 'Variant', 'Calories', 'Protein', 'Carbs', 'Fat', 'How to Prepare']

        with open(NUTRITION_PREP_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for row_data in data_to_save:
                if isinstance(row_data, dict):
                    filtered_row = {field: row_data.get(field, '') for field in fieldnames}
                    writer.writerow(filtered_row)
                else:
                    print(f"Skipping non-dictionary row during save: {row_data}")

        global nutrition_prep_data
        nutrition_prep_data = load_nutrition_prep_data() # Reload after saving

        return jsonify({'status': 'success', 'message': 'Data saved successfully!'})

    except Exception as e:
        print(f"Error saving data to {NUTRITION_PREP_FILE}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'Error saving data: {e}'}), 500

# --- Main execution (for local development only) ---
if __name__ == '__main__':
    app.run(debug=True)