import json
import os
import pandas as pd


def clean_ecommerce_pipeline():
  input_dir = os.path.join('data', 'input_data')
  output_dir = os.path.join('data', 'output_data')
  os.makedirs(output_dir, exist_ok=True)

  print(
      'Starting pipeline with typo correction, mojibake-safe numeric parsing,'
      ' & full imputation...'
  )

  def clean_columns(df):
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    return df

  def clean_text(series, case_style='title'):
    if series is None:
      return series
    s = series.astype(str).str.strip()
    s = s.replace(['nan', 'None', 'NAT', '', 'nan'], pd.NA)
    if case_style == 'lower':
      return s.str.lower()
    elif case_style == 'upper':
      return s.str.upper()
    elif case_style == 'capitalize':
      return s.str.capitalize()
    elif case_style == 'title':
      return s.str.title()
    return s

  # TYPO FIXER: Maps common spelling mistakes to a unified correct term
  def fix_typos(series, mapping_dict):
    cleaned = clean_text(series, 'capitalize')
    if cleaned is None:
      return cleaned
    # Map lowercase version for safe matching, then apply dictionary
    lower_s = cleaned.str.lower()
    for typo, correct in mapping_dict.items():
      lower_s = lower_s.replace(typo.lower(), correct)
    # Re-capitalize to match standard formatting
    return lower_s.str.capitalize()

  def clean_boolean(series):
    if series is None:
      return series
    s = (
        series.astype(str)
        .str.strip()
        .str.lower()
        .replace(['nan', 'none', 'nat', ''], pd.NA)
    )
    true_vals = {'true', 't', 'yes', 'y', '1', '1.0'}
    false_vals = {'false', 'f', 'no', 'n', '0', '0.0'}

    def map_bool(val):
      if pd.isna(val):
        return pd.NA
      if val in true_vals:
        return True
      if val in false_vals:
        return False
      return pd.NA

    return s.apply(map_bool).astype('boolean')

  def clean_numeric(series):
    if series is None:
      return series
    s = series.astype(str).str.strip()
    s = s.replace(['nan', 'None', 'NAT', '', 'nan'], pd.NA)
    stripped = s.str.replace(r'[^0-9.,\-]', '', regex=True)
    normalized = stripped.str.replace(',', '', regex=True)
    return pd.to_numeric(normalized, errors='coerce')

  def clean_dates(series):
    if series is None:
      return series
    return pd.to_datetime(series, format='mixed', errors='coerce')

  # Common typo mapping dictionaries
  status_typo_map = {
      'complted': 'Completed',
      'compleeted': 'Completed',
      'complete': 'Completed',
      'cancled': 'Cancelled',
      'canceled': 'Cancelled',
      'canelled': 'Cancelled',
      'pendng': 'Pending',
      'returnd': 'Returned',
      'faild': 'Failed',
  }

  # 0. Convert Suppliers JSON to CSV first
  json_supplier_path = os.path.join(input_dir, 'suppliers_json.txt')
  csv_supplier_path = os.path.join(output_dir, 'suppliers.csv')

  if os.path.exists(json_supplier_path):
    try:
      with open(json_supplier_path, 'r', encoding='utf-8') as f:
        suppliers_data = json.load(f)
    except UnicodeDecodeError:
      with open(json_supplier_path, 'r', encoding='latin1') as f:
        suppliers_data = json.load(f)
    suppliers_df_temp = pd.DataFrame(suppliers_data)
    suppliers_df_temp.to_csv(csv_supplier_path, index=False)

  # 1. Customers Data
  cust_raw = pd.read_csv(
      os.path.join(input_dir, 'customers.csv'), encoding='utf-8', on_bad_lines='skip'
  )
  customers = clean_columns(cust_raw)
  customers.drop_duplicates(subset=['customer_id'], keep='first', inplace=True)
  customers.dropna(subset=['customer_id'], inplace=True)

  customers['first_name'] = clean_text(
      customers['first_name'], 'title'
  ).fillna('Unknown')
  customers['last_name'] = clean_text(customers['last_name'], 'title').fillna(
      'Unknown'
  )
  customers['email'] = clean_text(customers['email'], 'lower').fillna(
      'noemail@domain.com'
  )
  customers['phone'] = clean_text(customers['phone'], 'lower').fillna('000-000')
  customers['city'] = clean_text(customers['city'], 'title').fillna('Unknown')
  customers['state'] = clean_text(customers['state'], 'upper').fillna('NA')
  customers['country'] = clean_text(customers['country'], 'title').fillna(
      'Unknown'
  )
  customers['signup_date'] = clean_dates(customers['signup_date']).fillna(
      pd.to_datetime('2023-01-01')
  )
  customers['customer_segment'] = clean_text(
      customers['customer_segment'], 'capitalize'
  ).fillna('Standard')
  customers['is_active'] = clean_boolean(customers['is_active']).fillna(True)

  customers.to_csv(os.path.join(output_dir, 'customers.csv'), index=False)
  valid_customers = set(customers['customer_id'])

  # 2. Suppliers Data
  supp_raw = pd.read_csv(csv_supplier_path, encoding='utf-8')
  suppliers = clean_columns(supp_raw)
  suppliers.drop_duplicates(subset=['supplier_id'], keep='first', inplace=True)
  suppliers.dropna(subset=['supplier_id'], inplace=True)

  suppliers['supplier_name'] = clean_text(
      suppliers['supplier_name'], 'title'
  ).fillna('Unknown Supplier')
  suppliers['country'] = clean_text(suppliers['country'], 'title').fillna(
      'Unknown'
  )
  suppliers['contract_start_date'] = clean_dates(
      suppliers['contract_start_date']
  ).fillna(pd.to_datetime('2023-01-01'))
  suppliers['is_preferred'] = clean_boolean(suppliers['is_preferred']).fillna(
      False
  )

  suppliers.to_csv(csv_supplier_path, index=False)
  valid_suppliers = set(suppliers['supplier_id'])

  # 3. Products Data
  prod_raw = pd.read_csv(
      os.path.join(input_dir, 'products.csv'), encoding='utf-8', on_bad_lines='skip'
  )
  products = clean_columns(prod_raw)
  products.drop_duplicates(subset=['product_id'], keep='first', inplace=True)
  products.dropna(subset=['product_id'], inplace=True)

  products['product_name'] = clean_text(
      products['product_name'], 'title'
  ).fillna('Unknown Product')
  products['category'] = clean_text(products['category'], 'title').fillna(
      'Uncategorized'
  )
  products['sub_category'] = clean_text(
      products['sub_category'], 'title'
  ).fillna('General')

  u_price = clean_numeric(products['unit_price'])
  c_price = clean_numeric(products['cost_price'])
  median_unit_price = u_price.median() if not pd.isna(u_price.median()) else 0.0
  median_cost_price = c_price.median() if not pd.isna(c_price.median()) else 0.0

  products['unit_price'] = u_price.fillna(median_unit_price)
  products['cost_price'] = c_price.fillna(median_cost_price)
  products['launch_date'] = clean_dates(products['launch_date']).fillna(
      pd.to_datetime('2023-01-01')
  )
  products['is_active'] = clean_boolean(products['is_active']).fillna(True)

  products.to_csv(os.path.join(output_dir, 'products.csv'), index=False)
  valid_products = set(products['product_id'])

  # 4. Orders Data
  ord_raw = pd.read_csv(
      os.path.join(input_dir, 'orders.csv'), encoding='utf-8', on_bad_lines='skip'
  )
  orders = clean_columns(ord_raw)
  orders.drop_duplicates(subset=['order_id'], keep='first', inplace=True)
  orders.dropna(subset=['order_id', 'customer_id'], inplace=True)

  orders['order_date'] = clean_dates(orders['order_date']).fillna(
      pd.to_datetime('2023-01-01')
  )
  # Applying typo correction to order_status
  orders['order_status'] = fix_typos(orders['order_status'], status_typo_map).fillna(
      'Pending'
  )
  orders['payment_method'] = clean_text(
      orders['payment_method'], 'title'
  ).fillna('Unknown')
  orders['channel'] = clean_text(orders['channel'], 'capitalize').fillna(
      'Online'
  )
  orders['promo_code'] = clean_text(orders['promo_code'], 'upper').fillna(
      'NONE'
  )
  orders['shipping_city'] = clean_text(
      orders['shipping_city'], 'title'
  ).fillna('Unknown')

  orders = orders[orders['customer_id'].isin(valid_customers)]
  orders.to_csv(os.path.join(output_dir, 'orders.csv'), index=False)
  valid_orders = set(orders['order_id'])

  # 5. Order Items Data
  item_raw = pd.read_csv(
      os.path.join(input_dir, 'order_items.csv'),
      encoding='utf-8',
      on_bad_lines='skip',
  )
  order_items = clean_columns(item_raw)
  order_items.drop_duplicates(
      subset=['order_item_id'], keep='first', inplace=True
  )
  order_items.dropna(
      subset=['order_item_id', 'order_id', 'product_id'], inplace=True
  )

  qty = clean_numeric(order_items['quantity'])
  item_p = clean_numeric(order_items['unit_price'])
  disc = clean_numeric(order_items['discount_pct'])
  line_t = clean_numeric(order_items['line_total'])

  median_item_qty = qty.median() if not pd.isna(qty.median()) else 1.0
  median_item_price = (
      item_p.median() if not pd.isna(item_p.median()) else 0.0
  )

  order_items['quantity'] = qty.fillna(median_item_qty)
  order_items['unit_price'] = item_p.fillna(median_item_price)
  order_items['discount_pct'] = disc.fillna(0.0)
  calculated_total = order_items['quantity'] * order_items['unit_price']
  order_items['line_total'] = line_t.fillna(calculated_total)

  order_items = order_items[
      order_items['order_id'].isin(valid_orders)
      & order_items['product_id'].isin(valid_products)
  ]
  order_items.to_csv(os.path.join(output_dir, 'order_items.csv'), index=False)
  valid_order_items = set(order_items['order_item_id'])

  # 6. Payments Data
  pay_raw = pd.read_csv(
      os.path.join(input_dir, 'payments.csv'), encoding='utf-8', on_bad_lines='skip'
  )
  payments = clean_columns(pay_raw)
  payments.drop_duplicates(subset=['payment_id'], keep='first', inplace=True)
  payments.dropna(subset=['payment_id', 'order_id'], inplace=True)

  payments['payment_date'] = clean_dates(payments['payment_date']).fillna(
      pd.to_datetime('2023-01-01')
  )
  amt = clean_numeric(payments['amount'])
  median_payment_amt = amt.median() if not pd.isna(amt.median()) else 0.0

  payments['amount'] = amt.fillna(median_payment_amt)
  # Applying typo correction to payment_status
  payments['payment_status'] = fix_typos(
      payments['payment_status'], status_typo_map
  ).fillna('Completed')
  payments['payment_method'] = clean_text(
      payments['payment_method'], 'title'
  ).fillna('Unknown')

  payments = payments[payments['order_id'].isin(valid_orders)]
  payments.to_csv(os.path.join(output_dir, 'payments.csv'), index=False)

  # 7. Returns Data
  ret_raw = pd.read_csv(
      os.path.join(input_dir, 'returns.csv'), encoding='utf-8', on_bad_lines='skip'
  )
  returns = clean_columns(ret_raw)
  returns.drop_duplicates(subset=['return_id'], keep='first', inplace=True)
  returns.dropna(subset=['return_id', 'order_item_id'], inplace=True)

  returns['return_date'] = clean_dates(returns['return_date']).fillna(
      pd.to_datetime('2023-01-01')
  )
  ref_amt = clean_numeric(returns['refund_amount'])
  returns['refund_amount'] = ref_amt.fillna(0.0)
  returns['return_reason'] = clean_text(
      returns['return_reason'], 'capitalize'
  ).fillna('Other')
  # Applying typo correction to return_status
  returns['return_status'] = fix_typos(
      returns['return_status'], status_typo_map
  ).fillna('Approved')

  returns = returns[returns['order_item_id'].isin(valid_order_items)]
  returns.to_csv(os.path.join(output_dir, 'returns.csv'), index=False)

  print(
      '\n✨ Typo Correction & Standardization Complete! All variations like'
      ' "complted" or "compleeted" are now standardized to "Completed".'
  )


if __name__ == '__main__':
  clean_ecommerce_pipeline()