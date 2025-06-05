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
    # Added Expiry Days to expected headers
    expected_headers_for_new_file = ['Product', 'Variant', 'Calories', 'Protein', 'Carbs', 'Fat', 'How to Prepare', 'Expiry Days']
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
                    'How to Prepare': row.get('How to Prepare', ''),
                    'Expiry Days': row.get('Expiry Days', '') # Load Expiry Days
                }
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
            missing_macros_log = []
            generation_date = datetime.now().date()
            generation_date_str = generation_date.strftime('%m/%d/%y') # Changed from '%Y-%m-%d'

            default_expiry_days = 11
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

            # Define your bundle configurations
            bundle_definitions = {
                ("by the lb pack #1", "by the lb"): [
                    {"product_name": "By The LB Protein - Balsamic Steak Tips 1.5lb", "variant_name": "By The LB", "count": 1},
                    {"product_name": "By The LB Protein - Honey Garlic Chicken 1.5LB", "variant_name": "By The LB", "count": 1},
                    {"product_name": "By The LB Carbs - Sweet Potatoes", "variant_name": "By The LB", "count": 1},
                    {"product_name": "By The LB Carbs - White Jasmine Rice", "variant_name": "Weight Loss", "count": 2},
                    {"product_name": "By The LB Vegetables - Garlicy Green Beans", "variant_name": "By The LB", "count": 1},
                    {"product_name": "By The LB Protein - Pulled Buffalo Chicken 1.5LB", "variant_name": "By The LB", "count": 1},
                ]
                # Add other bundle definitions here if needed:
                # ("bundle product name lower", "bundle variant name lower"): [ list of items ]
            }

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

                    # Customer details are needed for both bundle and regular items
                    customer_full_name = row.get('Customer', '').strip()
                    customer_parts = customer_full_name.split(' ', 1)
                    customer_first_name = customer_parts[0]
                    customer_last_name = customer_parts[1] if len(customer_parts) > 1 else ''
                    
                    product_lookup = product_name_original.lower()
                    variant_lookup = variant_name_original.lower()

                    # --- BUNDLE LOGIC ---
                    current_row_bundle_key = (product_lookup, variant_lookup)
                    if current_row_bundle_key in bundle_definitions:
                        bundle_items_list = bundle_definitions[current_row_bundle_key]
                        # 'quantity' is from the CSV for the bundle pack itself
                        for _ in range(quantity): # For each instance of the bundle pack
                            for item_spec in bundle_items_list:
                                item_product_name = item_spec["product_name"]
                                item_variant_name = item_spec["variant_name"]
                                item_bundle_count = item_spec["count"]

                                item_prod_lookup_key = item_product_name.lower()
                                item_var_lookup_key = item_variant_name.lower()
                                nutrition_key_for_item = (item_prod_lookup_key, item_var_lookup_key)
                                
                                item_nutrition_info = nutrition_prep_data.get(nutrition_key_for_item)

                                if not item_nutrition_info:
                                    missing_macros_log.append({
                                        "product": item_product_name,
                                        "variant": item_variant_name,
                                        "context": f"Part of bundle '{product_name_original}'" # Add context
                                    })
                                    item_nutrition_info = {} # Use empty dict for this sub-item

                                # Handle expiry for the sub-item
                                item_expiry_date_str = default_expiry_date.strftime('%m/%d/%y') # Default
                                item_custom_expiry_days_str = item_nutrition_info.get('Expiry Days', '').strip()
                                if item_custom_expiry_days_str:
                                    try:
                                        item_custom_expiry_days = int(item_custom_expiry_days_str)
                                        item_custom_expiry_date = generation_date + timedelta(days=item_custom_expiry_days)
                                        item_expiry_date_str = item_custom_expiry_date.strftime('%m/%d/%y')
                                    except ValueError:
                                        print(f"Warning: Invalid 'Expiry Days' value '{item_custom_expiry_days_str}' for bundle item {item_product_name} - {item_variant_name}. Using default expiry ({default_expiry_days} days).")

                                for _ in range(item_bundle_count): # For each unit of this specific item within the bundle
                                    label_data = {
                                        'generation_date': generation_date_str,
                                        'logo_url': logo_url,
                                        'customer_first_name': customer_first_name,
                                        'customer_last_name': customer_last_name,
                                        'product': item_product_name,
                                        'variant': item_variant_name,
                                        'modifiers': '', # Modifiers usually don't apply to individual bundle items
                                        'price': '',     # Price is for the bundle, not individual items
                                        'expiry_date': item_expiry_date_str,
                                        'calories': item_nutrition_info.get('Calories', ''),
                                        'protein': item_nutrition_info.get('Protein', ''),
                                        'carbs': item_nutrition_info.get('Carbs', ''),
                                        'fat': item_nutrition_info.get('Fat', ''),
                                        'preparation': item_nutrition_info.get('How to Prepare', '')
                                    }
                                    labels_data.append(label_data)
                        continue # IMPORTANT: Skip to the next row in the CSV, as bundle items have been processed
                    # --- END OF BUNDLE LOGIC ---

                    # --- REGULAR ITEM LOGIC (if not a bundle) ---
                    lookup_key = (product_lookup, variant_lookup)
                    nutrition_info = nutrition_prep_data.get(lookup_key) # Get data

                    if not nutrition_info:
                        missing_macros_log.append({
                            "product": product_name_original,
                            "variant": variant_name_original
                        })
                        nutrition_info = {} # Use empty dict to avoid errors later, label will show blank nutrition

                    current_expiry_date_str = default_expiry_date.strftime('%m/%d/%y')
                    custom_expiry_days_str = nutrition_info.get('Expiry Days', '').strip()
                    if custom_expiry_days_str:
                        try:
                            custom_expiry_days = int(custom_expiry_days_str)
                            custom_expiry_date = generation_date + timedelta(days=custom_expiry_days)
                            current_expiry_date_str = custom_expiry_date.strftime('%m/%d/%y')
                        except ValueError:
                            print(f"Warning: Invalid 'Expiry Days' value '{custom_expiry_days_str}' for {product_name_original} - {variant_name_original}. Using default expiry ({default_expiry_days} days).")
                    
                    # Customer name splitting already happened before the bundle check

                    for _ in range(quantity): # Loop for quantity of the regular (non-bundle) item
                        label_data = {
                            'generation_date': generation_date_str,
                            'logo_url': logo_url,
                            'customer_first_name': customer_first_name,
                            'customer_last_name': customer_last_name,
                            'product': product_name_original,
                            'variant': variant_name_original,
                            'modifiers': modifiers,
                            'price': f'{price_per_item:.2f}' if price_per_item else '',
                            'expiry_date': current_expiry_date_str,
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
            if not labels_data and not processed_rows and not missing_macros_log: #MODIFIED condition
                 return jsonify({'error': 'No valid data rows found in CSV to generate labels.'}), 400

            return jsonify({
                'labels': labels_data,
                'storage': storage_instruction,
                'missing_macros': missing_macros_log
            })

        except csv.Error as e: # For issues like malformed CSV structure
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
    # Ensure 'Expiry Days' is part of the headers for the editor
    fieldnames = ['Product', 'Variant', 'Calories', 'Protein', 'Carbs', 'Fat', 'How to Prepare', 'Expiry Days']
    error_message = None

    try:
        with open(NUTRITION_PREP_FILE, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            actual_fieldnames_from_csv = reader.fieldnames if reader.fieldnames else []
            
            # Check if actual fieldnames match expected fieldnames (order doesn't strictly matter for DictReader)
            # For simplicity, we'll just ensure all expected fields can be pulled.
            # The main check is whether actual_fieldnames_from_csv is empty or not.

            for row in reader:
                # Prioritize data from CSV for all defined fieldnames
                row_to_add = {field: row.get(field, '') for field in fieldnames}
                data_rows.append(row_to_add)

        if not data_rows and not os.path.exists(NUTRITION_PREP_FILE):
             error_message = f"{os.path.basename(NUTRITION_PREP_FILE)} not found. Add products and save to create it."
        elif not data_rows and actual_fieldnames_from_csv: # File exists with headers but no data rows
             pass # This is a valid state, table will be empty
        elif not actual_fieldnames_from_csv and os.path.exists(NUTRITION_PREP_FILE) and os.path.getsize(NUTRITION_PREP_FILE) > 0:
            # File exists and has content, but headers couldn't be read (e.g., not a CSV or malformed)
            error_message = f"Could not read headers from {os.path.basename(NUTRITION_PREP_FILE)}. File might be empty or corrupted."
        elif not actual_fieldnames_from_csv and os.path.exists(NUTRITION_PREP_FILE) and os.path.getsize(NUTRITION_PREP_FILE) == 0:
            # File exists but is completely empty (0 bytes)
            error_message = f"{os.path.basename(NUTRITION_PREP_FILE)} is empty. Add products and save to create it with headers."


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

        # Ensure 'Expiry Days' is part of the fieldnames for saving
        fieldnames = ['Product', 'Variant', 'Calories', 'Protein', 'Carbs', 'Fat', 'How to Prepare', 'Expiry Days']

        with open(NUTRITION_PREP_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for row_data in data_to_save:
                if isinstance(row_data, dict):
                    # Ensure all fields are present in the row, defaulting to empty string if not
                    # This handles cases where a row_data might be missing some keys
                    filtered_row = {field: row_data.get(field, '') for field in fieldnames}
                    writer.writerow(filtered_row)
                else:
                    # This case should ideally not happen if the frontend sends correct data
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