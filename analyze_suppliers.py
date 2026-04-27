import pandas as pd
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

path26 = r'd:\풀무원\Antigravity\eCS\26년.xlsx'

try:
    df = pd.read_excel(path26, sheet_name='VOC', header=None)
except Exception as e:
    print(f"Error reading Excel file: {e}")
    sys.exit(1)

results = []
for i in range(len(df)):
    metric = df.iloc[i, 2]
    if metric == 'VOC':
        supplier = df.iloc[i, 1]
        if pd.isna(supplier) or supplier == '생산처명' or '계' in str(supplier): continue
        
        voc = pd.to_numeric(df.iloc[i, 15], errors='coerce')
        # Production volume is usually the next row
        try:
            prod = pd.to_numeric(df.iloc[i+1, 15], errors='coerce')
        except:
            prod = 0
            
        if not pd.isna(voc) and not pd.isna(prod) and prod > 0:
            ppm = (voc / prod) * 1000000
            results.append({'Supplier': supplier, 'VOC': voc, 'Prod': prod, 'PPM': ppm})

sorted_res = sorted(results, key=lambda x: x['PPM'], reverse=True)
print('--- TOP 5 HIGHEST PPM SUPPLIERS (Calculated 26 Q1) ---')
for r in sorted_res[:5]:
    print(f"{r['Supplier']}: VOC={r['VOC']}, Prod={r['Prod']}, PPM={r['PPM']:.2f}")
