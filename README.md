# Gl🌍beRunners

GlobeRunners is a free open source PnP (print and play) card game powered by AI.<br>
Project details:
https://drive.google.com/drive/folders/1NJoHuItmpVYcfrMLCLYF9s6bC50vYajr <br>
Deckbuilding webapp: https://huggingface.co/spaces/jordyBonnet/GlobeRunners


## Things to try to uplaod deckbuilding webapp
https://www.youtube.com/watch?v=JtpDvI3qZ5U

## Project Files Overview

### Core Module

**[lib/artdesign/__init__.py](lib/artdesign/__init__.py)**  
Core module providing three main classes for the TCG card generation pipeline: `ArtDesign` for AI art generation via ComfyUI, `LayerImage` for card layer composition with effects like blur and transparency, and `PrintPDF` for generating print-ready PDFs. This module serves as the foundation for all card artwork generation and assembly, interfacing with the ComfyUI API running on localhost:8000 to create 816x1110 pixel cards ready for printing at 63x88mm.

### Card Pool Database

**[lib/cardpool/debug_YDB.ipynb](lib/cardpool/debug_YDB.ipynb)**  
The database generation pipeline that creates the entire card pool by combining game mechanics (mana, advancement, shield, conditions, effects) with AI art prompts. It constructs character descriptions with randomized attributes, builds action descriptions for effects, and generates faction-appropriate names. This notebook produces Parquet databases for each faction containing ~900+ cards total, with each row including card_id, mana, advancing, shield, condition, effect, prompt, and name fields that drive all downstream card generation.

### Art Generation & Composition

**[lib/artdesign/debug/debug_art_style.ipynb](lib/artdesign/debug/debug_art_style.ipynb)**  
Main production workflow for generating card artwork through experimentation with different art styles, model parameters, and faction character designs. Tests various artistic approaches (cottagecore, anime, pixel art, isometric) and optimizes model parameters (shift: 3.10, steps: 30, cfg: 5) for the 6 main factions (Dwarves, Demons, Twigs, Miaous, Orcs, Mummies). Processes the entire card pool database to generate individual card illustrations at approximately 43 seconds per image using the cozy soft pastel art style.

**[lib/artdesign/debug/debug_im_layers.ipynb](lib/artdesign/debug/debug_im_layers.ipynb)**  
Testing and development notebook for creating the card frame overlay system that layers icons, text, and visual effects on base artwork. Defines helper functions for adding mana costs, advancing values, shields, faction logos, condition/effect icons, biomes, and card names. The main `add_layers()` function combines all these elements to produce fully framed cards at 816x1110 resolution with all game markers and text overlays properly positioned.

**[lib/artdesign/debug/game_icons.ipynb](lib/artdesign/debug/game_icons.ipynb)**  
Dedicated notebook for generating all game icons and markers using AI art generation with consistent chibi/kawaii anime style parameters. Creates 624x624 pixel icons with white backgrounds for core mechanics (mana droplet, shield, cards, arrows), faction logos, effects (advancing, drawing, jumping, wrecking ball, grappling hook, unstoppable, rooted), and conditions (day/night, temperature, cataclysms, biomes, distance markers). These icons provide UI consistency across all card overlays and game components.

### Game Board & Special Cards

**[lib/artdesign/debug/earth_map.ipynb](lib/artdesign/debug/earth_map.ipynb)**  
Creates the game board "Earth" visualization by combining 4 biome images (Ocean, Mountain, Desert, Jungle) into a circular map with divisions for game tracking. Generates base biome artwork at 1500x1500 pixels, combines them into 4 quadrants with different configurations, adds division lines and tick marks, and labels with biome icons. Produces 4 earth map configurations with a circular mask and extended background suitable for a playmat at 1.2x scale.

**[lib/artdesign/debug/support_factions.ipynb](lib/artdesign/debug/support_factions.ipynb)**  
Development of support faction cards (Engineers, Mages, Doctors) that modify gameplay with special mechanics. Engineers provide boosts, trampolines, traps, mines, and refineries; Mages offer celestial reversal, thermic flux, apocalyptic ritual, and black hole effects; Doctors supply EPO/virus syringes, blood tests, laboratories, and advancement tokens. Generates support faction card artwork, special effect icons (house, tap, instant markers), and print-ready PDFs for each faction using a parallel pipeline to the main card generation system.

## How the Files Work Together

The project follows a clear data pipeline for card generation. [lib/cardpool/debug_YDB.ipynb](lib/cardpool/debug_YDB.ipynb) creates the foundational card pool database with AI prompts and game mechanics for all ~900+ cards. [lib/artdesign/debug_art_style.ipynb](lib/artdesign/debug/debug_art_style.ipynb) reads this database and generates card artwork using the `ArtDesign` class from [lib/artdesign/__init__.py](lib/artdesign/__init__.py), which interfaces with ComfyUI to produce base illustrations. [lib/artdesign/debug/debug_im_layers.ipynb](lib/artdesign/debug/debug_im_layers.ipynb) then adds frames and overlays using the `LayerImage` class, incorporating icons generated by [lib/artdesign/debug/game_icons.ipynb](lib/artdesign/debug/game_icons.ipynb). Finally, the `PrintPDF` class assembles print-ready PDFs. [lib/artdesign/debug/earth_map.ipynb](lib/artdesign/debug/earth_map.ipynb) and [lib/artdesign/debug/support_factions.ipynb](lib/artdesign/debug/support_factions.ipynb) operate as parallel systems for the game board and special cards, respectively, but share the same core classes and art generation approach to maintain visual consistency across all game components.


## Sources:
Comfyui + python: https://promptingpixels.com/tutorial/comfyui-with-python and<br>
https://www.youtube.com/watch?v=oVS1B1gflL8