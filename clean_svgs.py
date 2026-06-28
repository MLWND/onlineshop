import re

def clean_xiaomi():
    content = """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800" viewBox="0 0 800 800">
  <path fill="#f57921" d="M0 0h800v800H0z"/>
  <path d="M541.82 603.47V311.85c0-66.258-53.699-119.979-119.95-119.979H84.68c-2.601 0-4.705 2.094-4.705 4.667v406.93c0 2.573 2.104 4.658 4.705 4.658h90.066a4.693 4.693 0 0 0 4.705-4.687V284.048a4.7 4.7 0 0 1 4.706-4.695h193.68c36.367 0 65.865 29.479 65.865 65.855v258.22a4.69 4.69 0 0 0 4.688 4.688h88.744c2.58 0 4.689-2.091 4.689-4.66" fill="#faf9f5"/>
  <path d="M359.94 603.44a4.676 4.676 0 0 1-4.688 4.687h-90.046c-2.601 0-4.706-2.095-4.706-4.687V358.69a4.7 4.7 0 0 1 4.706-4.695h90.046a4.684 4.684 0 0 1 4.688 4.695v244.76-.01z" fill="#faf9f5"/>
  <path d="M720.02 603.44c0 2.592-2.104 4.687-4.707 4.687h-90.026c-2.603 0-4.727-2.095-4.727-4.687V196.58c0-2.602 2.124-4.705 4.727-4.705h90.026a4.702 4.702 0 0 1 4.707 4.705v406.86z" fill="#faf9f5"/>
</svg>"""
    with open('static/images/logos/xiaomi.svg', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Xiaomi SVG cleaned")

def clean_lenovo():
    content = """<svg version="1.1" id="图层_1" xmlns="http://www.w3.org/2000/svg" x="0px" y="0px" width="595.28px" height="213.684px" viewBox="0 0 595.28 213.684">
<rect x="10.593" y="12.658" fill="#DE2726" width="572.46" height="190.821"/>
<g>
	<path fill="#FFFFFF" d="M259.993,76.969c-8.46,0-18.074,3.928-23.95,11.763l0.011-0.011h-0.011 l0.011-10.524h-20.181v73.444h20.17v-41.786c0-7.528,5.834-15.517,16.634-15.517c8.343,0,16.973,5.802,16.973,15.517v41.786h20.17 v-45.529C289.819,89.23,277.728,76.969,259.993,76.969"/>
	<polygon fill="#FFFFFF" points="433.148,78.208 414.916,128.231 396.693,78.208 373.654,78.208 403.872,151.62 425.97,151.62 456.188,78.208 	"/>
	<path fill="#FFFFFF" d="M194.421,129.056c-8.492,6.29-13.341,7.793-21.091,7.793 c-6.957,0-12.409-2.17-16.263-5.95l51.574-21.398c-1.133-7.967-4.161-15.093-8.809-20.503 c-6.776-7.867-16.803-12.033-29.011-12.033c-22.171,0-38.89,16.364-38.89,37.968c0,22.171,16.75,37.958,41.113,37.958 c13.648,0,27.603-6.47,34.125-14.019L194.421,129.056z M155.669,100.332c3.441-4.611,8.905-7.322,15.522-7.322 c7.263,0,12.779,4.156,15.617,10.281l-35.227,14.606C150.619,110.401,152.535,104.535,155.669,100.332"/>
	<polygon fill="#FFFFFF" points="130.004,133.123 84.158,133.123 84.158,56.232 63.723,56.232 63.723,151.651 130.004,151.651 	"/>
	<path fill="#FFFFFF" d="M492.398,152.879c-22.055,0-39.334-16.422-39.334-37.947 c0-21.292,17.396-37.968,39.599-37.968c22.055,0,39.335,16.427,39.335,37.968C531.998,136.214,514.602,152.879,492.398,152.879 M492.398,94.249c-11.266,0-19.439,8.534-19.439,20.684c0,11.583,8.661,20.668,19.704,20.668c11.266,0,19.45-8.767,19.45-20.668 C512.113,103.333,503.441,94.249,492.398,94.249"/>
	<path fill="#FFFFFF" d="M337.137,152.879c-22.055,0-39.345-16.422-39.345-37.947 c0-21.292,17.407-37.968,39.61-37.968c22.055,0,39.334,16.427,39.334,37.968C376.735,136.214,359.34,152.879,337.137,152.879 M337.137,94.249c-11.266,0-19.45,8.534-19.45,20.684c0,11.583,8.671,20.668,19.715,20.668c11.266,0,19.439-8.767,19.439-20.668 C512.113,103.333,503.441,94.249,337.137,94.249"/>
	<path fill="#FFFFFF" d="M534.761,142.927H531.5v-1.864h8.544v1.864h-3.261v8.714h-2.022V142.927z M542.311,141.063h2.159l3.198,5.019l3.187-5.019h2.107v10.578h-1.97v-7.507l-3.261,5.061h-0.212l-3.251-5.061v7.507h-1.958 V141.063z"/>
</g>
</svg>"""
    with open('static/images/logos/lenovo.svg', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Lenovo SVG cleaned")

def clean_huawei():
    with open('media/svg/huawei.svg', 'r', encoding='utf-8') as f:
        orig = f.read()
    
    gradients = re.findall(r'(<radialGradient[^>]+>.*?</radialGradient>)', orig, re.DOTALL)
    
    paths_dict = {}
    for match in re.finditer(r'<path\s+id="SVGID_(\d+)_"\s+d="([^"]+)"', orig):
        paths_dict[match.group(1)] = match.group(2)
        
    clip_to_path = {}
    for match in re.finditer(r'<clipPath\s+id="SVGID_(\d+)_">\s*<use\s+xlink:href="#SVGID_(\d+)_"', orig):
        clip_to_path[match.group(1)] = match.group(2)
        
    new_paths = []
    for match in re.finditer(r'<polygon\s+clip-path="url\(#SVGID_(\d+)_\)"\s+fill="url\(#SVGID_(\d+)_\)"', orig):
        clip_id = match.group(1)
        grad_id = match.group(2)
        path_id = clip_to_path[clip_id]
        path_d = paths_dict[path_id]
        new_paths.append(f'<path d="{path_d}" fill="url(#SVGID_{grad_id}_)"/>')
        
    bottom_elements = []
    bottom_poly = re.search(r'<polygon\s+fill="#040000"\s+points="[^"]+"[^>]*>', orig).group(0)
    bottom_elements.append(bottom_poly)
    
    for match in re.finditer(r'<path\s+clip-path="url\(#SVGID_26_\)"\s+fill="#040000"\s+d="([^"]+)"', orig):
        bottom_elements.append(f'<path fill="#040000" d="{match.group(1)}"/>')
        
    bottom_rect = re.search(r'<rect\s+x="567\.536"\s+y="491\.944"\s+clip-path="url\(#SVGID_26_\)"\s+fill="#040000"\s+width="21\.979"\s+height="92\.501"\s*/>', orig).group(0)
    bottom_rect_clean = bottom_rect.replace('clip-path="url(#SVGID_26_)" ', '')
    bottom_elements.append(bottom_rect_clean)

    new_svg = []
    new_svg.append('<?xml version="1.0" encoding="utf-8"?>')
    new_svg.append('<svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="595.28px" height="595.28px" viewBox="0 0 595.28 595.28">')
    
    new_svg.append('<defs>')
    for grad in gradients:
        new_svg.append(grad)
    new_svg.append('</defs>')
    
    new_svg.append('<g>')
    for path in new_paths:
        new_svg.append(path)
    for el in bottom_elements:
        new_svg.append(el)
    new_svg.append('</g>')
    new_svg.append('</svg>')
    
    with open('static/images/logos/huawei.svg', 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_svg))
    print("Huawei SVG cleaned")

if __name__ == '__main__':
    clean_xiaomi()
    clean_lenovo()
    clean_huawei()
