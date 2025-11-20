""" 
This app serves as a web interface for the card pool, allowing users to filter and view cards, as well as generate a PDF for printing.

command to run: uv run cardpooUI/app.py

command to expose via cloudflare tunnel (C:\softs\cloudfared):
.\cloudflared-windows-amd64.exe tunnel --url http://0.0.0.0:8050/

use: https://free-url-shortener.rb.gy/ to reduce the given long url by cloudflare
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
import ast
import base64
import sys
HOME_DIR = r'c:\Users\jordy\Documents\python\projects\GenAI_TCG'
sys.path.append(HOME_DIR)
from lib.artdesign import Utils

# Load the card pool
db_path = os.path.join(os.path.dirname(__file__), '..', 'lib', 'cardpool', 'cardpool.parquet')
df = pl.read_parquet(db_path)
deck_path = os.path.join(os.path.dirname(__file__), 'decks_saved')
utils = Utils()

# Get unique filter options
def get_options(col):
    return [{'label': str(x), 'value': x} for x in sorted(df[col].unique().to_list())]



app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.MINTY, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True
)

# Serve card images from lib/artdesign/cards_framed
@app.server.route('/cards_framed/<path:filename>')
def serve_card_image(filename):
    cards_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib', 'artdesign', 'cards_framed'))
    return send_from_directory(cards_dir, filename)

# Serve game assets from lib/artdesign/cards_assets
@app.server.route('/cards_assets/<path:filename>')
def serve_game_asset(filename):
    assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib', 'artdesign', 'cards_assets'))
    return send_from_directory(assets_dir, filename)


app.layout = dmc.MantineProvider([
    dbc.Container([
        
        dmc.Drawer(     # Deck Drawer and Open Button
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
        dbc.Tooltip(
            "View your current deck",
            target="open-drawer-btn",
            placement="bottom",
            style={"fontSize": "0.95rem"}
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
        dbc.Tooltip(
            "Download a printable PDF of your deck (⚠️ wait for more than 30 seconds after clicking)",
            target="PDF-btn",
            placement="bottom",
            style={"fontSize": "0.95rem"}
        ),

        dmc.Modal(      # Modal for deck stats
            id="deck-stats-modal",
            title="Deck Statistics",
            centered=True,
            size="xl",
            zIndex=3000,  # <-- Add this line
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
        dbc.Tooltip(
            "Get some statistics about your deck",
            target="deck-stats-btn",
            placement="bottom",
            style={"fontSize": "0.95rem"}
        ),

        dmc.Button(     # Save deck
            "Save deck",
            id='save-deck-btn',
            leftSection=dmc.ThemeIcon(
                DashIconify(icon="mdi:content-save", width=14),
                radius='xl',
                size='sm',
                color="#caae60",
            ),
            size='xs',
            variant='light',
            style={'position': 'fixed', 'top': 8, 'left': 450, 'zIndex': 2100, 'padding': '0.3rem 0.7rem', 'fontSize': '0.9rem', 'color': '#caae60'},
        ),
        dcc.Download(id="save-deck-download"),
        dbc.Tooltip(
            "Save your current deck as a text file",
            target="save-deck-btn",
            placement="bottom",
            style={"fontSize": "0.95rem"}
        ),

        dcc.Upload(     # Load deck
            id='deck-upload',
            children=dmc.Button(     # Load deck
                "Load deck",
                id='load-deck-btn',
                leftSection=dmc.ThemeIcon(
                    DashIconify(icon="mdi:folder-upload", width=14),
                    radius='xl',
                    size='sm',
                    color="#c600d8",
                ),
                size='xs',
                variant='light',
                style={'position': 'fixed', 'top': 8, 'left': 600, 'zIndex': 2100, 'padding': '0.3rem 0.7rem', 'fontSize': '0.9rem', 'color': '#c600d8'},
            ),
            style={
                'display': 'inline-block',
            },
            multiple=False,
        ),
        dbc.Tooltip(
            "Load a previously saved deck",
            target="load-deck-btn",
            placement="bottom",
            style={"fontSize": "0.95rem"}
        ),
        
        html.Div([      # Top filter menu
            dbc.Row([
                dbc.Col([
                    dbc.Row([
                        dbc.Col([
                            dcc.Dropdown(id='faction-filter', options=get_options('faction'), multi=True, placeholder='Faction'),
                            dmc.Text("❗Select at least 3 filters to view cards", size="xs", c="dimmed", style={"marginBottom": "0.5rem"}),
                        ], xs=12, sm=6, md=4, lg=2, className='mb-2'),
                        dbc.Col([
                            dcc.Dropdown(id='mana-filter', options=get_options('mana'), multi=True, placeholder='Mana'),
                            dmc.Text("⚠️ Actualizing makes you lose current deck", size="xs", c="dimmed", style={"marginBottom": "0.5rem"}),
                        ], xs=12, sm=6, md=4, lg=2, className='mb-2'),
                        dbc.Col([
                            dcc.Dropdown(id='advancing-filter', options=get_options('advancing'), multi=True, placeholder='Advancing'),
                            dmc.Text("Cards loading time is quite long, sorry 😔", size="xs", c="dimmed", style={"marginBottom": "0.5rem"}),
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
                    # html.Div(id='cards-container', className='d-flex flex-wrap justify-content-center align-items-stretch')
                    html.Div(id='cards-container', className='d-flex flex-wrap justify-content-center align-items-start')
                ], width=12)
            ]),
        ], id='main-content', style={'backgroundColor': "#0e0e0e"}),

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
    ], fluid=True, style={'backgroundColor': '#0e0e0e'})
])


# Save deck callback: direct download
@app.callback(
    Output("save-deck-download", "data"),
    Input("save-deck-btn", "n_clicks"),
    State("deck", "data"),
    prevent_initial_call=True
)
def save_deck_to_txt(n_clicks, deck):
    if not n_clicks or not deck:
        return dash.no_update
    lines = [f"{card_id}" for card_id in deck]
    txt_content = "\n".join(lines)
    filename = "my_deck.txt"
    return dcc.send_bytes(txt_content.encode("utf-8"), filename)

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
        return dmc.Text("Your deck is empty. Add cards to your deck to see them here.", c="dimmed")
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
    n_min_filters = 3
    filters = [faction, mana, advancing, shield, condition, effect]
    num_set = sum(1 for f in filters if f)
    if num_set < n_min_filters:
        return presentation_page()
    
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
        card = dbc.Card([
            html.Div([
                dbc.CardImg(src=img_path, top=True, style={'objectFit': 'contain', 'width': '100%', 'height': 'auto', 'maxHeight': '350px', 'background': "#0e0e0e"}),
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
        ], className='m-2 card-responsive', style={'minHeight': '14rem', 'display': 'inline-block', 'border': '2px solid #0e0e0e'})
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

# Load deck from uploaded file
@app.callback(
    [Output('deck', 'data', allow_duplicate=True), Output('deck-drawer', 'opened', allow_duplicate=True)],
    Input('deck-upload', 'contents'),
    State('deck', 'data'),
    prevent_initial_call=True
)
def load_deck_from_file(contents, deck):
    if not contents:
        return dash.no_update, dash.no_update
    deck = list(deck) if deck else []
    _, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        card_ids = [line.strip() for line in decoded.decode('utf-8').splitlines() if line.strip()]
        for card_id in card_ids:
            if card_id not in deck:
                deck.append(card_id)
        return deck, True
    except Exception:
        return dash.no_update

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

# pdf generation callback
@app.callback(
    Output("pdf-download", "data"),
    Input("PDF-btn", "n_clicks"),
    State("deck", "data"),
    prevent_initial_call=True
)
def generate_pdf(n_clicks, deck):
    if not n_clicks or not deck:
        return dash.no_update
    
    pdf = utils.generate_pdf_from_deck(deck)
    
    return dcc.send_bytes(pdf, filename="GR_deck.pdf")

# First presentation page
def presentation_page():
    return html.Div(
        dmc.Center(
            dmc.Stack([
                dmc.Image(
                    src="/cards_assets/GlobeRunners_large_logo.png",
                    w=800,
                    fit="contain",
                    style={"marginBottom": "2rem"}
                ),
                dmc.Text("GlobeRunners is a free Print and Play (PnP) deck building card game.", size="md"),
                dmc.Text("Build your deck around six main factions and three support factions (5400+ cards) to find your signature playstyle and be the first to travel around the world.", size="md"),
                dmc.Image(
                    src="/cards_assets/GlobeRunners_cards_logo.png",
                    w=800,
                    fit="contain",
                    style={"marginTop": "1rem",
                        "marginBottom": "1rem"}
                ),
                html.A("Learn more about the game in these slides", href="https://docs.google.com/presentation/d/1z8EvBVcOxjh-tqTbaPtmv5BvFKnN5--I628QCtqlDOc/edit?slide=id.g39d59216dc3_0_117#slide=id.g39d59216dc3_0_117", style={"fontSize": "1.3rem"}),
                dmc.Divider(color="#000000", size="sm", my="lg"),
                dmc.Text("Download printable pdf starter decks below (⌚>30 seconds🙏):", size="md"),
                dmc.Group([
                    dmc.Button("Dwarves starter deck", id="download-dwarves-pdf-btn", color="#236CA5", size="md", variant="light"),
                    dmc.Button("Demons starter deck", id="download-demons-pdf-btn", color="#3E1B6A", size="md", variant="light"),
                    dmc.Button("Twigs starter deck", id="download-twigs-pdf-btn", color="#4A7D3A", size="md", variant="light"),
                    dmc.Button("Miaous starter deck", id="download-miaous-pdf-btn", color="#FF8253", size="md", variant="light"),
                    dmc.Button("Orcs starter deck", id="download-orcs-pdf-btn", color="#780B0B", size="md", variant="light"),
                    dmc.Button("Mummies starter deck", id="download-mummies-pdf-btn", color="#FDF5E6", size="md", variant="light"),
                ], align="center", gap="xs"),
                dmc.Text("Download printable pdf support factions below:", size="md"),
                dmc.Group([
                    dmc.Button("Engineers", id="download-Eng-pdf-btn", color="#B3633E", size="md", variant="light"),
                    dmc.Button("Doctors", id="download-doc-pdf-btn", color="#C06060", size="md", variant="light"),
                    dmc.Button("Mages", id="download-mag-pdf-btn", color="#6DA0C2", size="md", variant="light"),
                ], align="center", gap="xs"),
                dcc.Download(id="dwarves-pdf-download"),
                dcc.Download(id="demons-pdf-download"),
                dcc.Download(id="twigs-pdf-download"),
                dcc.Download(id="miaous-pdf-download"),
                dcc.Download(id="orcs-pdf-download"),
                dcc.Download(id="mummies-pdf-download"),
                dcc.Download(id="engineers-pdf-download"),
                dcc.Download(id="doctors-pdf-download"),
                dcc.Download(id="mages-pdf-download"),
                dmc.Divider(color="#000000", size="sm", my="lg"),
                dmc.Text("⚠️ All the illustrations in this project are AI-generated. While I am aware of the board game community's reservations regarding AI, this game is entirely a one-person passion project. Utilizing AI for the artwork was a necessary compromise to make the massive number of unique cards feasible.", size="xs"),
            ], align="center", gap="xs", justify="flex-start"),
            style={
                "color": "white",
                "width": "100%",
                "maxWidth": "1600px",
                "margin": "0 auto",
                "padding": "2rem 1rem"
            }
        ),
        style={
            "backgroundColor": "#0e0e0e",
            "minHeight": "100vh",
            "width": "100vw"
        }
    )

# download starter decks callbacks
@app.callback(
    [
        Output("dwarves-pdf-download", "data"),
        Output("demons-pdf-download", "data"),
        Output("twigs-pdf-download", "data"),
        Output("miaous-pdf-download", "data"),
        Output("orcs-pdf-download", "data"),
        Output("mummies-pdf-download", "data"),
        Output("engineers-pdf-download", "data"),
        Output("doctors-pdf-download", "data"),
        Output("mages-pdf-download", "data"),
    ],
    [
        Input("download-dwarves-pdf-btn", "n_clicks"),
        Input("download-demons-pdf-btn", "n_clicks"),
        Input("download-twigs-pdf-btn", "n_clicks"),
        Input("download-miaous-pdf-btn", "n_clicks"),
        Input("download-orcs-pdf-btn", "n_clicks"),
        Input("download-mummies-pdf-btn", "n_clicks"),
        Input("download-Eng-pdf-btn", "n_clicks"),
        Input("download-doc-pdf-btn", "n_clicks"),
        Input("download-mag-pdf-btn", "n_clicks"),
    ],
    prevent_initial_call=True
)
def download_dwarves_pdf(*n_clicks):
    ctx = callback_context
    if not ctx.triggered:
        return dash.no_update
    prop_id = ctx.triggered[0]['prop_id']
    if prop_id == "download-dwarves-pdf-btn.n_clicks":
        deck_pdf_path = os.path.join(deck_path, "Dwarves_starter_deck.pdf")
        return dcc.send_file(deck_pdf_path, filename="GR_dwarves_starter_deck.pdf"), dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    elif prop_id == "download-demons-pdf-btn.n_clicks":
        deck_pdf_path = os.path.join(deck_path, "Demons_starter_deck.pdf")
        return dash.no_update, dcc.send_file(deck_pdf_path, filename="GR_demons_starter_deck.pdf"), dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    elif prop_id == "download-twigs-pdf-btn.n_clicks":
        deck_pdf_path = os.path.join(deck_path, "Twigs_starter_deck.pdf")
        return dash.no_update, dash.no_update, dcc.send_file(deck_pdf_path, filename="GR_twigs_starter_deck.pdf"), dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    elif prop_id == "download-miaous-pdf-btn.n_clicks":
        deck_pdf_path = os.path.join(deck_path, "Miaous_starter_deck.pdf")
        return dash.no_update, dash.no_update, dash.no_update, dcc.send_file(deck_pdf_path, filename="GR_miaous_starter_deck.pdf"), dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    elif prop_id == "download-orcs-pdf-btn.n_clicks":
        deck_pdf_path = os.path.join(deck_path, "Orcs_starter_deck.pdf")
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dcc.send_file(deck_pdf_path, filename="GR_orcs_starter_deck.pdf"), dash.no_update, dash.no_update, dash.no_update, dash.no_update
    elif prop_id == "download-mummies-pdf-btn.n_clicks":
        deck_pdf_path = os.path.join(deck_path, "Mummies_starter_deck.pdf")
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dcc.send_file(deck_pdf_path, filename="GR_mummies_starter_deck.pdf"), dash.no_update, dash.no_update, dash.no_update
    elif prop_id == "download-Eng-pdf-btn.n_clicks":
        deck_pdf_path = os.path.join(deck_path, "Supfac_Eng.pdf")
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dcc.send_file(deck_pdf_path, filename="GR_engineers_support_faction.pdf"), dash.no_update, dash.no_update
    elif prop_id == "download-doc-pdf-btn.n_clicks":
        deck_pdf_path = os.path.join(deck_path, "Supfac_Doc.pdf")
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dcc.send_file(deck_pdf_path, filename="GR_doctors_support_faction.pdf"), dash.no_update
    elif prop_id == "download-mag-pdf-btn.n_clicks":
        deck_pdf_path = os.path.join(deck_path, "Supfac_Mag.pdf")
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dcc.send_file(deck_pdf_path, filename="GR_mages_support_faction.pdf")
    return dash.no_update

if __name__ == '__main__':
    # debug mode
    # ip = socket.gethostbyname(socket.gethostname())
    # print(f"Running on http://{ip}:8050")
    # app.run(debug=True, host=ip, port=8050)

    # production mode
    app.run(host="0.0.0.0", port=8050)

