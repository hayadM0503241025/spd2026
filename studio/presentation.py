"""Automatic visual defaults; no changes to indicator definitions or filters."""
PALETTE=('#16715B','#2F6CB4','#AA651C','#7B50A1','#AD4F65','#4E7843','#247D8A','#8C643C')
DEFAULT_COLUMNS=2
DEFAULT_PRIMARY_COLOR=PALETTE[0]


def automatic_color(index):
    return PALETTE[index % len(PALETTE)]


def apply_visual_defaults(design):
    design['dashboard']['columns']=DEFAULT_COLUMNS
    design['dashboard']['primary_color']=DEFAULT_PRIMARY_COLOR
    ordered=sorted(design['components'],key=lambda c:(c['row'],c['position']))
    design['components']=ordered
    for index,item in enumerate(ordered):
        item.update(color=automatic_color(index),row=index//DEFAULT_COLUMNS+1,
                    position=index%DEFAULT_COLUMNS+1,span=1)
    return design


def kpi_styles():
    rules=[]
    for color in PALETTE:
        rgb=[int(color[i:i+2],16) for i in (1,3,5)]
        background='#'+''.join(f'{round(channel*.08+255*.92):02x}' for channel in rgb)
        selector=f'[class*="st-key-kpi_{color[1:]}_"]'
        rules.append(f'{selector} {{background-color:{background}; border-top:4px solid {color}; border-radius:12px;}}')
        rules.append(f'{selector} [data-testid="stMetricValue"] {{color:{color};}}')
    return '\n'.join(rules)
