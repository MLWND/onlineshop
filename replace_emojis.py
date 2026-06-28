import os, re
path = 'c:/Users/XJL/Desktop/onlineshop-main/templates/'
for root, dirs, files in os.walk(path):
    for f in files:
        if f.endswith('.html'):
            filepath = os.path.join(root, f)
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
            def repl(m):
                var_name = m.group(1)
                if var_name == 'ba':
                    alt = 'ba.brand_name'
                elif var_name == 'product.brand':
                    alt = 'product.brand.brand_name'
                elif var_name == 'report.brand':
                    alt = 'report.brand.brand_name'
                else:
                    alt = f'{var_name}.brand_name'
                return f'<img src=\"{{{{ {var_name}.logo_url }}}}\" class=\"brand-logo-img\" alt=\"{{{{ {alt} }}}}\">'
            new_content = re.sub(r'\{\{\s*([a-zA-Z0-9_\.]+)\.logo_emoji\s*\}\}', repl, content)
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as file:
                    file.write(new_content)
                print(f'Updated {f}')

