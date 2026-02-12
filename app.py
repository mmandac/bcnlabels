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
    expected_headers_for_new_file = ['Product', 'Variant', 'Calories', 'Protein', 'Carbs', 'Fat', 'How to Prepare', 'Expiry Days']
    try:
        if not os.path.exists(NUTRITION_PREP_FILE):
            return data
        with open(NUTRITION_PREP_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
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
                    'Expiry Days': row.get('Expiry Days', '')
                }
    except Exception as e:
        print(f"Error reading {NUTRITION_PREP_FILE}: {e}")
    return data

nutrition_prep_data = load_nutrition_prep_data()

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/process_csv', methods=['POST'])
def process_csv():
    global nutrition_prep_data
    nutrition_prep_data = load_nutrition_prep_data()

    if 'csv_file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['csv_file']
    if not file or file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        content_bytes = file.read()
        content_string = content_bytes.decode('utf-8')
        csv_file_like_object = io.StringIO(content_string)
        reader = csv.DictReader(csv_file_like_object)

        if not reader.fieldnames:
            return jsonify({'error': 'CSV file is empty or does not contain headers.'}), 400

        labels_data = []
        missing_macros_log = []
        generation_date = datetime.now().date()
        generation_date_str = generation_date.strftime('%m/%d/%y') 

        default_expiry_days = 11
        default_expiry_date = generation_date + timedelta(days=default_expiry_days)

        storage_instruction = ""
        if os.path.exists(STORAGE_INSTRUCTION_FILENAME):
            with open(STORAGE_INSTRUCTION_FILENAME, 'r', encoding='utf-8') as f:
                storage_instruction = f.read().strip()

        selected_branding = request.form.get('branding')
        logo_url = url_for('static', filename='beast_coast_logo.png') if selected_branding == 'beast_coast' else None

        bundle_definitions = {
            ("by the lb pack #1", "by the lb"): [
                {"product_name": "By The LB Protein - Balsamic Steak Tips 1.5lb", "variant_name": "By The LB", "count": 1},
                {"product_name": "By The LB Protein - Honey Garlic Chicken 1.5LB", "variant_name": "By The LB", "count": 1},
                {"product_name": "By The LB Carbs - Sweet Potatoes", "variant_name": "By The LB", "count": 1},
                {"product_name": "By The LB Carbs - White Jasmine Rice", "variant_name": "Weight Loss", "count": 2},
                {"product_name": "By The LB Vegetables - Garlicy Green Beans", "variant_name": "By The LB", "count": 1},
                {"product_name": "By The LB Protein - Pulled Buffalo Chicken 1.5LB", "variant_name": "By The LB", "count": 1},
            ],
            ("top sellers -5 pack", "5 meal pack"): [
                {"product_name": "Blackened Chicken & Shrimp Alfredo -TSPK", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Greek Chicken Bowl -TSPK", "variant_name": "Fit", "count": 1},
                {"product_name": "Healthy Steak Nachos -TSPK", "variant_name": "Fit", "count": 1},
                {"product_name": "Honey Garlic Sticky Chicken -TSPK", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Korean Ground Beef -TSPK", "variant_name": "Weight Loss", "count": 1},
            ],
            ("top sellers -10 pack", "10 meal pack"): [
                {"product_name": "Balsamic Marinated Tenderloin Steak Tips -TSPK", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Blackened Chicken & Shrimp Alfredo -TSPK", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Blackened Chicken Tacos -TSPK", "variant_name": "Athlete (3)", "count": 1},
                {"product_name": "Fit Cheeseburger Bowl -TSPK", "variant_name": "Fit", "count": 1},
                {"product_name": "Greek Chicken Bowl -TSPK", "variant_name": "Fit", "count": 1},
                {"product_name": "Ground Beef Taco Bowl #2 -TSPK", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Healthy Steak Nachos -TSPK", "variant_name": "Fit", "count": 1},
                {"product_name": "Honey Garlic Sticky Chicken -TSPK", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Korean Ground Beef -TSPK", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Surf & Turf Chimichurri Steak & Shrimp -TSPK", "variant_name": "Weight Loss", "count": 1},
            ],
            ("beast mode -15 pack", "15 meal pack"): [
                {"product_name": "Balsamic Marinated Tenderloin Steak Tips -TSPK", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Blackened Chicken & Shrimp Alfredo -TSPK", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Blackened Chicken Tacos -TSPK", "variant_name": "Athlete (3)", "count": 1},
                {"product_name": "Fit Cheeseburger Bowl -TSPK", "variant_name": "Fit", "count": 1},
                {"product_name": "Greek Chicken Bowl -TSPK", "variant_name": "Fit", "count": 1},
                {"product_name": "Ground Beef Taco Bowl #2 -TSPK", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Healthy Steak Nachos -TSPK", "variant_name": "Fit", "count": 1},
                {"product_name": "Honey Garlic Sticky Chicken -TSPK", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Korean Ground Beef -TSPK", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Surf & Turf Chimichurri Steak & Shrimp -TSPK", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Protein Egg Bites (6)", "variant_name": "Default", "count": 2},
                {"product_name": "Blueberry Muffin Bites (8)", "variant_name": "Fit", "count": 1},
                {"product_name": "Blueberry Protein Muffin Bites (4) & Turkey Sausage (2)", "variant_name": "Fit", "count": 1},
                {"product_name": "Egg & Bacon Breakfast Flatbread", "variant_name": "Weight Loss", "count": 1},
            ],
            ("beast mode -21 pack", "21 meal pack"): [
                {"product_name": "Balsamic Marinated Tenderloin Steak Tips -TSPK", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Blackened Chicken & Shrimp Alfredo -TSPK", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Blackened Chicken Tacos -TSPK", "variant_name": "Athlete (3)", "count": 1},
                {"product_name": "Fit Cheeseburger Bowl -TSPK", "variant_name": "Fit", "count": 1},
                {"product_name": "Greek Chicken Bowl -TSPK", "variant_name": "Fit", "count": 1},
                {"product_name": "Ground Beef Taco Bowl #2 -TSPK", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Healthy Steak Nachos -TSPK", "variant_name": "Fit", "count": 1},
                {"product_name": "Honey Garlic Sticky Chicken -TSPK", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Korean Ground Beef -TSPK", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Surf & Turf Chimichurri Steak & Shrimp -TSPK", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Protein Egg Bites (6)", "variant_name": "Default", "count": 1},
                {"product_name": "Blueberry Muffin Bites (8)", "variant_name": "Fit", "count": 1},
                {"product_name": "Blueberry Protein Muffin Bites (4) & Turkey Sausage (2)", "variant_name": "Fit", "count": 1},
                {"product_name": "Egg & Bacon Breakfast Flatbread", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Korean BBQ Meatballs -TSPK", "variant_name": "Weight Loss", "count": 1},
                {"product_name": "Chicken Parmesan Quesadilla", "variant_name": "Athlete", "count": 1},
                {"product_name": "Protein Egg Bites (4) & Turkey Sausage (4)", "variant_name": "Fit", "count": 1},
                {"product_name": "Egg & Bacon Breakfast Bowl -TSPK", "variant_name": "Fit", "count": 1},
                {"product_name": "Chocolate Chip Protein Muffin Bites (8)", "variant_name": "Fit", "count": 1},
                {"product_name": "Shepherds Pie -TSPK", "variant_name": "Fit", "count": 1},
                {"product_name": "Healthy Chicken Penne Alfredo -TSPK", "variant_name": "Weight Loss", "count": 1},
            ]
        }

        for row in reader:
            qty = int(float(row.get('Quantity', '1').strip() or 1))
            prod_orig = row.get('Product', '').strip()
            var_orig = row.get('Variant', '').strip()
            if not prod_orig: continue

            price = float(row.get('Price', '0').replace('$', '').strip() or 0)
            price_per = price / qty if qty else 0
            mods = row.get('Modifiers', '').strip().replace('nan', '').replace('(1x)', '').replace('(2x)', '').strip()
            name_parts = row.get('Customer', '').strip().split(' ', 1)
            f_name, l_name = name_parts[0], name_parts[1] if len(name_parts) > 1 else ''

            # Bundle Check
            bundle_key = (prod_orig.lower(), var_orig.lower())
            if bundle_key in bundle_definitions:
                for _ in range(qty):
                    for item in bundle_definitions[bundle_key]:
                        i_prod, i_var = item["product_name"], item["variant_name"]
                        nutri = nutrition_prep_data.get((i_prod.lower(), i_var.lower()), {})
                        
                        if not nutri:
                            missing_macros_log.append({"product": i_prod, "variant": i_var, "context": f"Bundle {prod_orig}"})

                        exp_days = nutri.get('Expiry Days', '').strip()
                        exp_str = (generation_date + timedelta(days=int(exp_days))).strftime('%m/%d/%y') if exp_days.isdigit() else default_expiry_date.strftime('%m/%d/%y')

                        for _ in range(item["count"]):
                            labels_data.append({
                                'generation_date': generation_date_str, 'logo_url': logo_url,
                                'customer_first_name': f_name, 'customer_last_name': l_name,
                                'product': i_prod, 'variant': i_var, 'modifiers': '', 
                                'price': '', 'expiry_date': exp_str,
                                'calories': nutri.get('Calories', ''), 'protein': nutri.get('Protein', ''),
                                'carbs': nutri.get('Carbs', ''), 'fat': nutri.get('Fat', ''),
                                'preparation': nutri.get('How to Prepare', '')
                            })
                continue

            # Regular Item
            nutri = nutrition_prep_data.get(bundle_key, {})
            if not nutri:
                missing_macros_log.append({"product": prod_orig, "variant": var_orig})

            exp_days = nutri.get('Expiry Days', '').strip()
            exp_str = (generation_date + timedelta(days=int(exp_days))).strftime('%m/%d/%y') if exp_days.isdigit() else default_expiry_date.strftime('%m/%d/%y')

            for _ in range(qty):
                labels_data.append({
                    'generation_date': generation_date_str, 'logo_url': logo_url,
                    'customer_first_name': f_name, 'customer_last_name': l_name,
                    'product': prod_orig, 'variant': var_orig, 'modifiers': mods,
                    'price': f'{price_per:.2f}' if price_per else '', 'expiry_date': exp_str,
                    'calories': nutri.get('Calories', ''), 'protein': nutri.get('Protein', ''),
                    'carbs': nutri.get('Carbs', ''), 'fat': nutri.get('Fat', ''),
                    'preparation': nutri.get('How to Prepare', '')
                })

        # --- FINAL SORTING: Product then Variant ---
        labels_data.sort(key=lambda x: (x['product'].lower(), x['variant'].lower()))

        return jsonify({'labels': labels_data, 'storage': storage_instruction, 'missing_macros': missing_macros_log})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/edit_data_page', methods=['GET'])
def edit_data_page():
    data_rows = []
    fieldnames = ['Product', 'Variant', 'Calories', 'Protein', 'Carbs', 'Fat', 'How to Prepare', 'Expiry Days']
    if os.path.exists(NUTRITION_PREP_FILE):
        with open(NUTRITION_PREP_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data_rows.append({field: row.get(field, '') for field in fieldnames})
    return render_template('edit_data.html', headers=fieldnames, data=data_rows)

@app.route('/save_data', methods=['POST'])
def save_data():
    try:
        data = request.get_json()
        fieldnames = ['Product', 'Variant', 'Calories', 'Protein', 'Carbs', 'Fat', 'How to Prepare', 'Expiry Days']
        with open(NUTRITION_PREP_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow({field: row.get(field, '') for field in fieldnames})
        return jsonify({'status': 'success', 'message': 'Data saved!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)