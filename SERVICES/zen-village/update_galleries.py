#!/usr/bin/env python3
"""
Update property gallery data in index.html to include all available photos.
Run on server: python3 /tmp/update_galleries.py
"""
import os
import re
import json

IMGBASE = "/opt/fpai/apps/zen-village/frontend/public/images/accommodations"
FILE = "/opt/fpai/apps/zen-village/frontend/public/index.html"

def get_images(subdir, max_images=20):
    """Get all image files in a directory, sorted sensibly."""
    path = os.path.join(IMGBASE, subdir)
    if not os.path.isdir(path):
        return ["/images/placeholder.svg"]
    
    images = []
    for root, dirs, files in os.walk(path):
        for f in files:
            ext = f.lower().split('.')[-1]
            if ext in ('jpg', 'jpeg', 'png', 'webp', 'avif'):
                rel = os.path.relpath(os.path.join(root, f), os.path.join(IMGBASE, ".."))
                images.append("/images/" + rel)
    
    # Sort: main first, then numbered, then UUIDs
    def sort_key(path):
        name = os.path.basename(path).split('.')[0]
        if name == 'main':
            return (0, '')
        try:
            return (1, int(name))
        except ValueError:
            return (2, name)
    
    images.sort(key=sort_key)
    return images[:max_images] if images else ["/images/placeholder.svg"]

# Build updated property data
properties = {
    'hearth-house': {
        'name': 'The Hearth House',
        'zone': 'Village Heart',
        'desc': 'A warm 3-bedroom communal home at the heart of Zen Village. Perfect for families or groups seeking connection. Features shared living spaces, full kitchen, and easy access to all community amenities.',
        'prices': {'night': 130, 'week': 780, 'month': 2200},
        'images': get_images('hearth-house', 15),
    },
    'green-casita': {
        'name': 'Green Casita',
        'zone': 'Village Heart',
        'desc': 'A cozy cabana nestled near the Singing Dome chapel. Intimate and peaceful, ideal for solo travelers or couples seeking quiet reflection.',
        'prices': {'night': 95, 'week': 570, 'month': 1600},
        'images': get_images('green-casita', 15),
    },
    'the-vista': {
        'name': 'Cloud Cabin (Hilltop)',
        'zone': 'Escape Ridge',
        'desc': 'Perched on the hillside with breathtaking panoramic views over the valley. Features a spacious deck perfect for sunrise meditation and evening stargazing. 4x4 vehicle required for hilltop access.',
        'prices': {'night': 75, 'week': 450, 'month': 1400},
        'images': get_images('the-vista', 20),
    },
    'the-nido': {
        'name': 'Summit Cabin (Hilltop)',
        'zone': 'Escape Ridge',
        'desc': 'A cozy hillside cabin offering solitude and stunning views. The perfect nest for writers, artists, or anyone seeking deep retreat. 4x4 vehicle required for hilltop access.',
        'prices': {'night': 75, 'week': 450, 'month': 1400},
        'images': get_images('the-nido', 20),
    },
    'astro-alpha': {
        'name': 'Astro Alpha',
        'zone': 'Village Heart',
        'desc': 'A unique geodesic dome with panoramic views and immersive nature experience. Sleep under the stars in this architectural wonder.',
        'prices': {'night': 55, 'week': 330, 'month': 1000},
        'images': get_images('astro-alpha', 15),
    },
    'astro-sol': {
        'name': 'Astro Sol',
        'zone': 'Village Heart',
        'desc': 'Sister to Astro Alpha, this geodesic dome offers the same magical design with its own unique character and views.',
        'prices': {'night': 55, 'week': 330, 'month': 1000},
        'images': get_images('astro-sol', 20),
    },
    'riverlight': {
        'name': 'Riverlight Cabin',
        'zone': 'River Grove',
        'desc': 'A wooden cabin immersed in nature, steps from the river. Wake to flowing water and the calm energy of the River Grove zone.',
        'prices': {'night': 65, 'week': 390, 'month': 1200},
        'images': get_images('riverlight', 20),
    },
    'camp-spring': {
        'name': 'Jungle Platform',
        'zone': 'Village Heart',
        'desc': 'An open-air platform surrounded by jungle. Bring your own tent or hammock and camp under the stars. Access to all village amenities including sauna and river.',
        'prices': {'night': 45, 'week': 270, 'month': 800},
        'images': get_images('camp-spring', 10),
    },
    'glamp-grove': {
        'name': 'River House',
        'zone': 'River Grove',
        'desc': 'A comfortable riverside home with modern amenities and direct river access. Perfect for those seeking comfort without sacrificing the nature experience.',
        'prices': {'night': 85, 'week': 510, 'month': 1500},
        'images': get_images('glamp-grove', 15),
    },
    'zen-casa': {
        'name': 'Zen Casa (3BR Home)',
        'zone': 'River Grove',
        'desc': 'A spacious 3-bedroom home perfect for families or groups. Beautiful covered porch with prayer flags, full kitchen, and easy access to the river.',
        'prices': {'night': 195, 'week': 1170, 'month': 3500},
        'images': get_images('zen-casa', 25),
    },
}

# Build JS object string
lines = ["const propertyData = {"]
for key, prop in properties.items():
    img_list = ",\n      ".join(f"'{img}'" for img in prop['images'])
    lines.append(f"  '{key}': {{")
    lines.append(f"    name: '{prop['name']}',")
    lines.append(f"    zone: '{prop['zone']}',")
    lines.append(f"    desc: '{prop['desc']}',")
    lines.append(f"    prices: {{ night: {prop['prices']['night']}, week: {prop['prices']['week']}, month: {prop['prices']['month']} }},")
    lines.append(f"    images: [\n      {img_list}\n    ]")
    lines.append(f"  }},")
lines.append("};")
new_data = "\n".join(lines)

# Read existing HTML
with open(FILE, "r") as f:
    html = f.read()

# Find and replace the propertyData block
pattern = r'const propertyData = \{.*?\};'
match = re.search(pattern, html, re.DOTALL)
if match:
    html = html[:match.start()] + new_data + html[match.end():]
    with open(FILE, "w") as f:
        f.write(html)
    print("Updated propertyData in index.html")
    print(f"\nProperty gallery summary:")
    for key, prop in properties.items():
        count = len(prop['images'])
        has_real = prop['images'][0] != '/images/placeholder.svg'
        print(f"  {'[REAL]' if has_real else '[PLACEHOLDER]'} {prop['name']}: {count} photos")
else:
    print("ERROR: Could not find propertyData block in index.html")
