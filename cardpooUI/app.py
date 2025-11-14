""" command to run: uv run cardpooUI/app.py
This app serves as a web interface for the card pool, allowing users to filter and view cards, as well as generate a PDF for printing.

"""

from flask import send_from_directory
import polars as pl
import dash
from dash import html, dcc, Input, Output, State, callback_context
import dash_mantine_components as dmc
import dash_bootstrap_components as dbc
from dash_iconify import DashIconify
import os
import socket
from flask import send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import io
import ast

# Load the card pool
db_path = os.path.join(os.path.dirname(__file__), '..', 'lib', 'cardpool', 'cardpool.parquet')
print(db_path)
df = pl.read_parquet(db_path)

# Get unique filter options
def get_options(col):
    return [{'label': str(x), 'value': x} for x in sorted(df[col].unique().to_list())]



app = dash.Dash(__name__, external_stylesheets=[dbc.themes.MINTY, dbc.icons.BOOTSTRAP])

# Serve card images from lib/artdesign/cards_framed
@app.server.route('/cards_framed/<path:filename>')
def serve_card_image(filename):
    cards_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib', 'artdesign', 'cards_framed'))
    return send_from_directory(cards_dir, filename)

app.layout = dmc.MantineProvider([
    dbc.Container([
        # Deck Drawer and Open Button
        dmc.Drawer(
            id='deck-drawer',
            # title='Your Deck',
            padding='md',
            size='100vw',
            position='right',
            zIndex=2000,
            children=[
                html.Div(id='deck-content')
            ],
        ),
        dmc.Button(     # Your deck
            "Your Deck",
            id='open-drawer-btn',
            leftSection=dmc.ThemeIcon(
                DashIconify(icon="mdi:cards", width=14),
                radius='xl',
                size='sm',
                color='blue',
            ),
            size='xs',
            variant='light',
            style={'position': 'fixed', 'top': 8, 'left': 8, 'zIndex': 2100, 'padding': '0.3rem 0.7rem', 'fontSize': '0.9rem'},
        ),

        dmc.Button(     # PDF to print
            "PDF to print",
            id='PDF-btn',
            leftSection=dmc.ThemeIcon(
                DashIconify(icon="mdi:file-pdf-box", width=14),
                radius='xl',
                size='sm',
                color='red',
            ),
            size='xs',
            variant='light',
            style={'position': 'fixed', 'top': 8, 'left': 150, 'zIndex': 2100, 'padding': '0.3rem 0.7rem', 'fontSize': '0.9rem', 'color': 'red'},
        ),
        dcc.Download(id="pdf-download"),

        # Modal for deck stats
        dmc.Modal(
            id="deck-stats-modal",
            title="Deck Statistics",
            centered=True,
            size="xl",
            children=[
                dmc.Stack([
                    dmc.Text("Deck Mana Histogram", size="lg"),
                    dcc.Graph(id="deck-mana-histogram"),
                    dmc.Text("Number of Cards: ", id="deck-num-cards", size="md"),
                    dmc.Text("Conditions in Deck:", size="md"),
                    html.Ul(id="deck-conditions-list"),
                ], gap="md")
            ],
            opened=False,
            withCloseButton=True,
        ),
        dmc.Button(     # Deck stats
            "Deck stats",
            id='deck-stats-btn',
            leftSection=dmc.ThemeIcon(
                DashIconify(icon="mdi:graph-bar", width=14),
                radius='xl',
                size='sm',
                color='green',
            ),
            size='xs',
            variant='light',
            style={'position': 'fixed', 'top': 8, 'left': 300, 'zIndex': 2100, 'padding': '0.3rem 0.7rem', 'fontSize': '0.9rem', 'color': 'green'},
        ),

        dmc.Button(     # Save deck
            "Save deck",
            id='save-deck-btn',
            leftSection=dmc.ThemeIcon(
                DashIconify(icon="mdi:content-save", width=14),
                radius='xl',
                size='sm',
                color='yellow',
            ),
            size='xs',
            variant='light',
            style={'position': 'fixed', 'top': 8, 'left': 450, 'zIndex': 2100, 'padding': '0.3rem 0.7rem', 'fontSize': '0.9rem', 'color': 'yellow'},
        ),

        # Modal for deck name input
        dmc.Modal(
            id="save-deck-modal",
            title="Save Deck",
            centered=True,
            size="sm",
            children=[
                dmc.Text("Enter a name for your deck:"),
                dmc.TextInput(id="deck-name-input", placeholder="Deck name", style={"marginBottom": 10}),
                dmc.Button("Save", id="confirm-save-deck-btn", color="yellow", fullWidth=True)
            ],
            opened=False,
            withCloseButton=True,
        ),
        dcc.Download(id="save-deck-download"),

        html.Div([      # Top filter menu
            dbc.Row([
                dbc.Col([
                    dbc.Row([
                        dbc.Col([
                            dcc.Dropdown(id='faction-filter', options=get_options('faction'), multi=True, placeholder='Faction'),
                        ], xs=12, sm=6, md=4, lg=2, className='mb-2'),
                        dbc.Col([
                            dcc.Dropdown(id='mana-filter', options=get_options('mana'), multi=True, placeholder='Mana'),
                        ], xs=12, sm=6, md=4, lg=2, className='mb-2'),
                        dbc.Col([
                            dcc.Dropdown(id='advancing-filter', options=get_options('advancing'), multi=True, placeholder='Advancing'),
                        ], xs=12, sm=6, md=4, lg=2, className='mb-2'),
                        dbc.Col([
                            dcc.Dropdown(id='shield-filter', options=get_options('shield'), multi=True, placeholder='Shield'),
                        ], xs=12, sm=6, md=4, lg=2, className='mb-2'),
                        dbc.Col([
                            dcc.Dropdown(id='condition-filter', options=get_options('condition'), multi=True, placeholder='Condition'),
                        ], xs=12, sm=6, md=4, lg=2, className='mb-2'),
                        dbc.Col([
                            dcc.Dropdown(id='effect-filter', options=get_options('effect'), multi=True, placeholder='Effect'),
                        ], xs=12, sm=6, md=4, lg=2, className='mb-2'),
                    ], className='g-2 flex-wrap'),
                ], width=12, className='bg-white p-3 shadow-sm'),
            ], style={'marginTop': '25px'}),
        ], id='filter-bar'),

        html.Div([      # Cards container
            dbc.Row([
                dbc.Col([
                    html.Div(id='cards-container', className='d-flex flex-wrap justify-content-center align-items-stretch')
                ], width=12)
            ]),
        ], id='main-content', style={'backgroundColor': '#0a0a0a'}),

        dcc.Store(id='deck', data=[]),
        dcc.Store(id='show-alert', data=False),
        dcc.Store(id='last-added-card', data=None),
        dcc.Store(id='last-removed-card', data=None),
        dbc.Alert(
            id='deck-alert',
            children='',
            color='success',
            is_open=False,
            duration=2000,
            fade=True,
            style={
                'position': 'fixed',
                'top': 10,
                'left': '50%',
                'transform': 'translateX(-50%)',
                'zIndex': 3000,
                'minWidth': '400px',
                'fontSize': '1rem',
                'fontWeight': 'bold',
                'textAlign': 'center',
                'padding': '1.5rem 2rem',
            }
        ),
    ], fluid=True, style={'backgroundColor': '#0a0a0a'})
])

# Open/close the deck drawer
@app.callback(
    Output("save-deck-modal", "opened"),
    [Input("save-deck-btn", "n_clicks"), Input("save-deck-modal", "onClose"), Input("confirm-save-deck-btn", "n_clicks")],
    [State("save-deck-modal", "opened")],
    prevent_initial_call=False
)
def toggle_save_deck_modal(open_click, close_event, confirm_click, opened):
    ctx = callback_context
    if not ctx.triggered:
        print('\nNew loaded page ------------------')
        return dash.no_update
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    if trigger == "save-deck-btn":
        return True
    if trigger == "save-deck-modal" or trigger == "confirm-save-deck-btn":
        return False
    return dash.no_update

# Save deck callback
@app.callback(
    Output("save-deck-download", "data"),
    Input("confirm-save-deck-btn", "n_clicks"),
    State("deck", "data"),
    State("deck-name-input", "value"),
    prevent_initial_call=True
)
def save_deck_to_txt(n_clicks, deck, deck_name):
    if not n_clicks or not deck or not deck_name:
        return dash.no_update
    import collections
    # Count occurrences
    counts = collections.Counter(deck)
    lines = [f"{count} x {card_id}" for card_id, count in counts.items()]
    txt_content = "\n".join(lines)
    # Clean deck name for filename
    safe_name = "".join(c for c in deck_name if c.isalnum() or c in (" ", "_", "-"))
    safe_name = safe_name.strip().replace(" ", "_")
    filename = f"{safe_name}.txt"
    # Save in decks_saved folder
    folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cardpooUI', 'decks_saved'))
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(txt_content)
    # No download, just save to file
    return dash.no_update

# Deck Stats modal opening
@app.callback(
    Output("deck-stats-modal", "opened"),
    [Input("deck-stats-btn", "n_clicks"), Input("deck-stats-modal", "onClose")],
    [State("deck-stats-modal", "opened")],
    prevent_initial_call=True
)
def toggle_deck_stats_modal(open_click, close_event, opened):
    ctx = callback_context
    if not ctx.triggered:
        return dash.no_update
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    if trigger == "deck-stats-btn":
        return True
    if trigger == "deck-stats-modal":
        return False
    return dash.no_update

# Deck stats content callback
@app.callback(
    [Output("deck-mana-histogram", "figure"), Output("deck-num-cards", "children"), Output("deck-conditions-list", "children")],
    Input("deck", "data")
)
def update_deck_stats(deck):
    import plotly.graph_objs as go
    if not deck:
        fig = go.Figure()
        fig.update_layout(title="No cards in deck", xaxis_title="Mana", yaxis_title="Count")
        return fig, "Number of Cards: 0", []
    deck_df = df.filter(pl.col('card_id').is_in(deck))
    # Mana histogram
    mana_counts = deck_df.group_by("mana").len().sort("mana")
    mana_x = mana_counts["mana"].to_list()
    # Find the column that is the count column (should be the last one, not 'card_id')
    count_col = [col for col in mana_counts.columns if col not in ("mana", "condition", "effect", "faction", "shield", "name")][-1]
    mana_y = mana_counts[count_col].to_list()
    fig = go.Figure([go.Bar(x=mana_x, y=mana_y)])
    fig.update_layout(title="Mana Cost Histogram", xaxis_title="Mana Cost", yaxis_title="Count", template="plotly_white")
    # Number of cards
    num_cards = len(deck)
    # Conditions list
    cond_counts = deck_df.group_by("condition").len().sort("condition")
    cond_count_col = [col for col in cond_counts.columns if col not in ("mana", "condition", "effect", "faction", "shield", "name")][-1]
    cond_items = [html.Li(f"{cond_counts['condition'][i]}: {cond_counts[cond_count_col][i]}") for i in range(len(cond_counts))]
    return fig, f"Number of Cards: {num_cards}", cond_items

# Deck drawer opening
@app.callback(
    Output('deck-drawer', 'opened'),
    Input('open-drawer-btn', 'n_clicks'),
    State('deck-drawer', 'opened'),
    prevent_initial_call=True
)
def open_drawer(n, opened):
    return not opened if n else opened

# Show deck content in the drawer
@app.callback(
    Output('deck-content', 'children'),
    Input('deck', 'data')
)
def show_deck(deck):
    if not deck:
        return dmc.Text("Your deck is empty.", c="dimmed")
    # Show card images and ids in the deck
    cards = []
    # Show cards at 300x450 for much greater visibility
    for card_id in deck:
        img_path = f"/cards_framed/{card_id}.png"
        cards.append(
            dmc.Stack([
                html.Div([
                    dmc.Image(src=img_path, w=int(816/3.5), h=int(1110/3.5), fit="contain", style={"marginTop": 0, "paddingTop": 0}),
                    dmc.Button(
                        "Remove",
                        id={'type': 'rem-from-deck', 'index': card_id},
                        color="red",
                        size="xs",
                        variant="filled",
                        style={
                            'position': 'absolute',
                            'top': '10px',
                            'right': '10px',
                            'zIndex': 2,
                            'padding': '2px 8px',
                            'fontSize': '0.7rem',
                            'borderRadius': '8px',
                            'fontWeight': 'bold',
                        },
                        n_clicks=0
                    )
                ], style={'position': 'relative', 'width': f'{int(816/3.5)}px', 'height': f'{int(1110/3.5)}px', 'display': 'inline-block'}),
            ], gap=0, align="center", mb=8, style={"gap": 0, "rowGap": 0, "padding": 0, "margin": 0})
        )
    return dmc.Group(cards, gap="xs", align="start", style={"flexWrap": "wrap"})

# Card filtering
@app.callback(
    Output('cards-container', 'children'),
    [
        Input('faction-filter', 'value'),
        Input('mana-filter', 'value'),
        Input('advancing-filter', 'value'),
        Input('shield-filter', 'value'),
        Input('condition-filter', 'value'),
        Input('effect-filter', 'value'),
    ],
    State('deck', 'data')
)
def update_cards(faction, mana, advancing, shield, condition, effect, deck):
    # Show message if fewer than 2 filters are set
    filters = [faction, mana, advancing, shield, condition, effect]
    num_set = sum(1 for f in filters if f)
    if num_set < 2:
        return [html.Div("Select at least two filters to view cards.", style={
            'color': 'white', 'fontSize': '1.5rem', 'textAlign': 'center', 'marginTop': '2rem'})]
    filtered = df
    if faction:
        filtered = filtered.filter(pl.col('faction').is_in(faction))
    if mana:
        filtered = filtered.filter(pl.col('mana').is_in(mana))
    if advancing:
        filtered = filtered.filter(pl.col('advancing').is_in(advancing))
    if shield:
        filtered = filtered.filter(pl.col('shield').is_in(shield))
    if condition:
        filtered = filtered.filter(pl.col('condition').is_in(condition))
    if effect:
        filtered = filtered.filter(pl.col('effect').is_in(effect))
    cards = []
    for row in filtered.iter_rows(named=True):
        img_path = f"/cards_framed/{row['card_id']}.png"
        is_in_deck = row['card_id'] in deck
        card = dbc.Card([
            html.Div([
                dbc.CardImg(src=img_path, top=True, style={'objectFit': 'contain', 'width': '100%', 'height': 'auto', 'maxHeight': '350px', 'background': "#0a0a0a"}),
                dmc.Button(
                    'Add',
                    id={'type': 'add-to-deck', 'index': row['card_id']},
                    color='teal',
                    size="xs",
                    variant="filled",
                    style={
                        'position': 'absolute',
                        'top': '6px',
                        'right': '20px',
                        'zIndex': 2,
                        'padding': '2px 8px',
                        'fontSize': '0.7rem',
                        'borderRadius': '8px',
                        'fontWeight': 'bold',
                    },
                    n_clicks=0
                )
            ], style={'position': 'relative', 'width': '100%'}),
        ], className='m-2 card-responsive', style={'minHeight': '14rem', 'display': 'inline-block', 'border': '2px solid #0a0a0a'})
        cards.append(card)
    return cards


# Add/remove a card to the deck using Button
@app.callback(
    [Output('deck', 'data'), Output('show-alert', 'data'), Output('last-added-card', 'data'), Output('last-removed-card', 'data')],
    [
        Input({'type': 'add-to-deck', 'index': dash.ALL}, 'n_clicks'),
        Input({'type': 'rem-from-deck', 'index': dash.ALL}, 'n_clicks'),
    ],
    State('deck', 'data'),
    prevent_initial_call=True
)
def update_deck(add_n_clicks, rem_n_clicks, deck):
    ctx = callback_context
    deck = list(deck) if deck else []
    if not ctx.triggered:
        return deck, False, None, None
    if len(ctx.triggered) > 1:  # Prevent the triggering when update_cards is called !!!
        return deck, False, None, None
    
    prop_id = ctx.triggered[0]['prop_id']
    # print(f'ctx.triggered --> {ctx.triggered}')
    card_id = ast.literal_eval(prop_id.split('.')[0])['index']

    if 'add-to-deck' in prop_id and prop_id.endswith('.n_clicks'):
        if card_id not in deck:
            deck.append(card_id)
            return deck, True, card_id, None
        
    elif 'rem-from-deck' in prop_id and prop_id.endswith('.n_clicks'):
        if card_id in deck:
            deck.remove(card_id)
            return deck, False, None, card_id
    
    return deck, False, None, None

""" A implementer !!!!
CAS 1 - click direct add -> remove

update_deck: prop_id --> {"index":"Dem21_2f33a6","type":"add-to-deck"}.checked
        checked: True, value: True, card_id not in deck: True ---> carte à ajouter au deck

update_deck: prop_id --> {"index":"Dem21_2f33a6","type":"add-to-deck"}.checked
        checked: False, value: True, card_id not in deck: False ---> carte à retirer du deck


CAS 2 - click après changement filtre

update_deck: prop_id --> {"index":"Dem21_2f33a6","type":"add-to-deck"}.checked
        checked: True, value: True, card_id not in deck: True ---> carte à ajouter au deck

update_deck: prop_id --> {"index":"Dem21_2f33a6","type":"add-to-deck"}.checked
        checked: True, value: False, card_id not in deck: False ---> carte à retirer du deck

        
CAS 3 - click après changement filtre mais dans le drawer deck cette fois-ci

update_deck: prop_id --> {"index":"Dem21_2f33a6","type":"add-to-deck"}.checked
        checked: True, value: True, card_id not in deck: True

update_deck: prop_id --> {"index":"Dem21_2f33a6","type":"add-to-deck"}.checked
        checked: True, value: False, card_id not in deck: False

"""

# Show/hide alert and set its content when card is added or removed
@app.callback(
    [Output('deck-alert', 'is_open'), Output('deck-alert', 'children')],
    [Input('show-alert', 'data'), Input('last-added-card', 'data'), Input('last-removed-card', 'data')],
    prevent_initial_call=True
)
def show_alert(added, card_id, removed_id):
    if added and card_id:
        # Try to get card name from df
        try:
            name = df.filter(pl.col('card_id') == card_id)['name'][0]
        except Exception:
            name = card_id
        return True, f"Added to deck: {name} ({card_id})"
    if removed_id:
        try:
            name = df.filter(pl.col('card_id') == removed_id)['name'][0]
        except Exception:
            name = removed_id
        return True, f"Removed from deck: {name} ({card_id})"
    return False, ''

# PDF GENERATION CALLBACK
@app.callback(
    Output("pdf-download", "data"),
    Input("PDF-btn", "n_clicks"),
    State("deck", "data"),
    prevent_initial_call=True
)
def generate_pdf(n_clicks, deck):
    if not n_clicks or not deck:
        return dash.no_update
    # Get the image folder
    cards_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib', 'artdesign', 'cards_framed'))
    # PDF settings
    page_width, page_height = A4  # in points (1 pt = 1/72 inch)
    # Card size in mm
    card_width_mm = 63
    card_height_mm = 88
    # Convert mm to points: 1 mm = 2.83465 pt
    mm_to_pt = 2.83465
    card_width_pt = card_width_mm * mm_to_pt
    card_height_pt = card_height_mm * mm_to_pt
    # Spacing between cards (0.5mm)
    spacing_mm = 0.5
    spacing_pt = spacing_mm * mm_to_pt

    # Compute how many cards fit per row/column, accounting for spacing between cards
    cols = int((page_width + spacing_pt) // (card_width_pt + spacing_pt))
    rows = int((page_height + spacing_pt) // (card_height_pt + spacing_pt))

    # Compute total grid size
    grid_width = cols * card_width_pt + (cols - 1) * spacing_pt
    grid_height = rows * card_height_pt + (rows - 1) * spacing_pt

    # Center the grid on the page
    margin_x = (page_width - grid_width) / 2 if page_width > grid_width else 0
    margin_y = (page_height - grid_height) / 2 if page_height > grid_height else 0
    # Duplicate deck list
    card_ids = deck
    # Prepare PDF
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)

    for idx, card_id in enumerate(card_ids):        
        img_path = os.path.join(cards_dir, f"{card_id}.png")
        col = idx % cols
        row = (idx // cols) % rows
        if idx > 0 and idx % (cols * rows) == 0:
            c.showPage()
        x = margin_x + col * (card_width_pt + spacing_pt)
        y = page_height - margin_y - ((row + 1) * card_height_pt + row * spacing_pt)

        try:
            # Draw a black rectangle behind the card image, slightly larger than the card
            border_mm = spacing_mm * 2  # Make the border larger than spacing
            border_pt = border_mm * mm_to_pt
            c.setFillColorRGB(0, 0, 0)
            c.rect(
                x - border_pt / 2,
                y - border_pt / 2,
                card_width_pt + border_pt,
                card_height_pt + border_pt,
                fill=1,
                stroke=0
            )
            c.drawImage(ImageReader(img_path), x, y, width=card_width_pt, height=card_height_pt, preserveAspectRatio=False, mask='auto')
        except Exception as e:
            continue
    c.save()
    pdf_buffer.seek(0)
    return dcc.send_bytes(pdf_buffer.getvalue(), filename="deck_print.pdf")




if __name__ == '__main__':
    ip = socket.gethostbyname(socket.gethostname())
    print(f"Running on http://{ip}:8050")
    app.run(debug=True, host=ip, port=8050)

