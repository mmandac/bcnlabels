import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
import csv
import io
from datetime import datetime, timedelta

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))

# Define the name of your nutrition data CSV file
NUTRITION_PREP_FILE = 'nutrition_prep_data.csv'

# --- Helper Function to Load Nutrition and Preparation Data ---
def load_nutrition_prep_data():
    """
    Loads nutrition and preparation data from the CSV file.
    Returns a dictionary where keys are (product_name_lower, variant_name_lower)
    and values are dictionaries of the row data.
    """
    data = {}
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
                # Store all found fields, 'Expiry Days' will just be missing if not in CSV
                data[key] = {
                    'Product': row.get('Product', ''),
                    'Variant': row.get('Variant', ''),
                    'Calories': row.get('Calories', ''),
                    'Protein': row.get('Protein', ''),
                    'Carbs': row.get('Carbs', ''),
                    'Fat': row.get('Fat', ''),
                    'How to Prepare': row.get('How to Prepare', '')
                    # 'Expiry Days' is no longer explicitly handled here for the editor's core fieldset
                    # If it exists in the CSV, DictReader puts it in 'row', but we won't use it for editor fieldnames
                }
                # If 'Expiry Days' is still needed for label generation from an existing CSV column
                # and you don't want to remove it from the CSV file itself immediately,
                # you could still add it to data[key] like:
                # if 'Expiry Days' in row:
                #    data[key]['Expiry Days'] = row.get('Expiry Days', '')

    except FileNotFoundError:
        print(f"Error: {NUTRITION_PREP_FILE} not found. Please create this file.")
        # Define expected headers for a new file if it's created via editor
        print("Expected headers for new file via editor: Product, Variant, Calories, Protein, Carbs, Fat, How to Prepare")
    except Exception as e:
        print(f"Error reading {NUTRITION_PREP_FILE}: {e}")
    return data

# --- Initialize nutrition_prep_data when the app starts ---
nutrition_prep_data = load_nutrition_prep_data()

# --- Route for the main page (label generator) ---
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# --- Route to process the uploaded CSV for label generation ---
@app.route('/process_csv', methods=['POST'])
def process_csv():
    global nutrition_prep_data # Use the globally loaded data
    nutrition_prep_data = load_nutrition_prep_data() # Reload data in case it was edited

    if 'csv_file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['csv_file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and file.filename.endswith('.csv'):
        try:
            csv_data_stream = io.TextIOWrapper(file.stream, encoding='utf-8')
            reader = csv.DictReader(csv_data_stream)
            labels_data = []
            generation_date = datetime.now().date()
            generation_date_str = generation_date.strftime('%Y-%m-%d')
            
            # Default Expiry: 11 days from generation if not specified by product
            default_expiry_date = generation_date + timedelta(days=11)


            # --- Storage Instruction Logic ---
            storage_instruction = "" # Default is now an empty string
            try:
                with open('storage_instruction.txt', 'r', encoding='utf-8') as f_storage:
                    custom_storage_instruction = f_storage.read().strip()
                    if custom_storage_instruction: # Only override if the file is not empty
                        storage_instruction = custom_storage_instruction
            except FileNotFoundError:
                print("'storage_instruction.txt' not found. Using default storage instruction.")
            except Exception as e_storage:
                print(f"Error reading 'storage_instruction.txt': {e_storage}. Using default.")
            # --- End Storage Instruction Logic ---

            selected_branding = request.form.get('branding')
            logo_url = None
            # (Keep your existing branding logic here)
            if selected_branding == 'beast_coast':
                logo_url = url_for('static', filename='beast_coast_logo.png')
            elif selected_branding == 'resilient':
                logo_url = url_for('static', filename='resilient_logo.png')
            elif selected_branding == 'nh_meal_prep':
                logo_url = url_for('static', filename='nh_meal_prep_logo.png')
            elif selected_branding == 'long_island':
                logo_url = url_for('static', filename='long_island_logo.png')


            for row_number, row in enumerate(reader, 1):
                try:
                    quantity_str = row.get('Quantity', '1').strip()
                    quantity = int(float(quantity_str)) if quantity_str else 1 # Handle potential float like "1.0" then int

                    price_str = row.get('Price', '0').replace('$', '').strip()
                    price = float(price_str) if price_str else 0.0
                    price_per_item = price / quantity if quantity else 0.0

                    modifiers = row.get('Modifiers', '').strip()
                    if modifiers.lower() == 'nan':
                        modifiers = ''
                    else:
                        # Example: remove common quantity indicators if they are part of modifiers
                        modifiers = modifiers.replace('(1x)', '').replace('(2x)', '').strip()


                    product_name_original = row.get('Product', '').strip()
                    variant_name_original = row.get('Variant', '').strip()
                    product_lookup = product_name_original.lower()
                    variant_lookup = variant_name_original.lower()
                    
                    lookup_key = (product_lookup, variant_lookup)
                    nutrition_info = nutrition_prep_data.get(lookup_key, {})

                    # --- Expiry Date Logic ---
                    current_expiry_date_str = default_expiry_date.strftime('%Y-%m-%d') # Default
                    custom_expiry_days_str = nutrition_info.get('Expiry Days', '').strip()
                    if custom_expiry_days_str:
                        try:
                            custom_expiry_days = int(custom_expiry_days_str)
                            custom_expiry_date = generation_date + timedelta(days=custom_expiry_days)
                            current_expiry_date_str = custom_expiry_date.strftime('%Y-%m-%d')
                        except ValueError:
                            print(f"Warning: Invalid 'Expiry Days' value '{custom_expiry_days_str}' for {product_name_original} - {variant_name_original}. Using default expiry.")
                    # --- End Expiry Date Logic ---

                    customer_full_name = row.get('Customer', '').strip()
                    customer_parts = customer_full_name.split(' ', 1)
                    customer_first_name = customer_parts[0]
                    customer_last_name = customer_parts[1] if len(customer_parts) > 1 else ''


                    for _ in range(quantity):
                        label_data = {
                            'generation_date': generation_date_str,
                            'logo_url': logo_url,
                            'customer_first_name': customer_first_name,
                            'customer_last_name': customer_last_name,
                            'product': product_name_original, # Use original casing from CSV for display
                            'variant': variant_name_original, # Use original casing from CSV for display
                            'modifiers': modifiers,
                            'price': f'{price_per_item:.2f}' if price_per_item else '', # Handle zero price
                            'expiry_date': current_expiry_date_str,
                            'calories': nutrition_info.get('Calories', ''), # Match CSV header
                            'protein': nutrition_info.get('Protein', ''),   # Match CSV header
                            'carbs': nutrition_info.get('Carbs', ''),     # Match CSV header
                            'fat': nutrition_info.get('Fat', ''),         # Match CSV header
                            'preparation': nutrition_info.get('How to Prepare', '') # Match CSV header
                        }
                        labels_data.append(label_data)
                except ValueError as e:
                    return jsonify({'error': f'Error processing row {row_number} (ValueError): {row}. Details: {e}. Please check data types (e.g., Quantity, Price).'}), 400
                except Exception as e:
                    return jsonify({'error': f'Unexpected error processing row {row_number}: {row}. Details: {e}'}), 400
            
            if not labels_data and reader.line_num <= 1 : # No data rows processed
                 return jsonify({'error': 'CSV file seems to be empty or contains only headers.'}), 400


            return jsonify({'labels': labels_data, 'storage': storage_instruction })
        except UnicodeDecodeError:
            return jsonify({'error': 'Error decoding CSV file. Please ensure it is UTF-8 encoded.'}), 400
        except csv.Error as e:
             return jsonify({'error': f'Error parsing CSV structure: {e}. Please check CSV format, especially headers and delimiters.'}), 400
        except Exception as e:
            # Log the full error to the server console for debugging
            print(f"Unhandled error in /process_csv: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'An unexpected error occurred while processing the CSV file: {e}'}), 500
            
    return jsonify({'error': 'Invalid file format. Only CSV files are allowed.'}), 400

# --- Route for displaying and editing nutrition data ---
@app.route('/edit_data_page', methods=['GET'])
def edit_data_page():
    data_rows = []
    # Define fieldnames for the editor, EXCLUDING 'Expiry Days'
    fieldnames = ['Product', 'Variant', 'Calories', 'Protein', 'Carbs', 'Fat', 'How to Prepare'] # <-- MODIFIED
    error_message = None

    try:
        with open(NUTRITION_PREP_FILE, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            actual_fieldnames_from_csv = reader.fieldnames if reader.fieldnames else []

            for row in reader:
                # Populate row_to_add with values for the defined editor fieldnames
                row_to_add = {field: row.get(field, '') for field in fieldnames}
                data_rows.append(row_to_add)

        if not data_rows and not os.path.exists(NUTRITION_PREP_FILE): # File doesn't exist
             error_message = f"{NUTRITION_PREP_FILE} not found. You can add products below and save to create the file."
        elif not data_rows and actual_fieldnames_from_csv: # File exists but is empty or has only headers
             pass # No error, just an empty table will be shown
        elif not actual_fieldnames_from_csv and os.path.exists(NUTRITION_PREP_FILE): # File exists but might be unreadable as CSV by DictReader
            error_message = f"Could not read headers from {NUTRITION_PREP_FILE}. File might be empty or corrupted."


    except FileNotFoundError: # Should be caught by the os.path.exists check above, but good fallback.
        error_message = f"{NUTRITION_PREP_FILE} not found. You can add products below and save to create the file."
    except Exception as e:
        error_message = f"Error reading data: {e}"
        print(f"Error in /edit_data_page: {e}")

    return render_template('edit_data.html', headers=fieldnames, data=data_rows, error_message=error_message)


# --- Route for saving nutrition data from the editor ---
@app.route('/save_data', methods=['POST'])
def save_data():
    try:
        data_to_save = request.get_json() # Expecting a JSON array of objects (rows)
        
        if not isinstance(data_to_save, list):
            return jsonify({'status': 'error', 'message': 'Invalid data format. Expected a list of products.'}), 400

        # Define the fieldnames for the CSV in the desired order.
        # This ensures consistent column order when writing.
        fieldnames = ['Product', 'Variant', 'Calories', 'Protein', 'Carbs', 'Fat', 'How to Prepare', 'Expiry Days']

        with open(NUTRITION_PREP_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            # extrasaction='ignore' means if a row in data_to_save has more keys than fieldnames, those extra keys are ignored.
            # extrasaction='raise' (default) would raise an error.
            writer.writeheader()
            for row_data in data_to_save:
                # Ensure row_data is a dictionary
                if isinstance(row_data, dict):
                     # Create a new dict for writing to ensure only specified fieldnames are written,
                     # and in the correct order, providing defaults for missing keys.
                    filtered_row = {field: row_data.get(field, '') for field in fieldnames}
                    writer.writerow(filtered_row)
                else:
                    # Log or handle rows that are not dictionaries, if necessary
                    print(f"Skipping non-dictionary row: {row_data}")

        # Reload data into the application's global variable after saving
        global nutrition_prep_data
        nutrition_prep_data = load_nutrition_prep_data()

        return jsonify({'status': 'success', 'message': 'Data saved successfully!'})

    except Exception as e:
        print(f"Error saving data to {NUTRITION_PREP_FILE}: {e}") # Log error to server console
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'Error saving data: {e}'}), 500

# --- Main execution ---
if __name__ == '__main__':
    # app.run(debug=True) # Only for local development
    # For production, the WSGI server (like Gunicorn) will run 'app' directly.
    # If you still want to run it locally with python app.py
    app.run(debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true')