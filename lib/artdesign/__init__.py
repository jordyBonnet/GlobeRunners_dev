import websocket  # websocket-client
import uuid
import json
import urllib.request
import urllib.parse
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import io
import numpy as np
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import io


class ArtDesignClient:
    """ class using ComfyUI for AI art generation """
    def __init__(self, server_address="127.0.0.1:8000"):
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())
        self.workflow = self._load_workflow()

    def _load_workflow(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "image_qwen_python.json")
        with open(path, 'r') as file:
            return json.load(file)

    def queue_prompt(self, prompt, prompt_id):
        p = {"prompt": prompt, "client_id": self.client_id, "prompt_id": prompt_id}
        data = json.dumps(p).encode('utf-8')
        req = urllib.request.Request(f"http://{self.server_address}/prompt", data=data)
        urllib.request.urlopen(req).read()
    
    def get_image(self, filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen(f"http://{self.server_address}/view?{url_values}") as response:
            return response.read()

    def get_history(self, prompt_id):
        with urllib.request.urlopen(f"http://{self.server_address}/history/{prompt_id}") as response:
            return json.loads(response.read())

    def get_images(self, ws, prompt):
        prompt_id = str(uuid.uuid4())
        self.queue_prompt(prompt, prompt_id)
        output_images = {}
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        break
            else:
                continue

        history = self.get_history(prompt_id)[prompt_id]
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            images_output = []
            if 'images' in node_output:
                for image in node_output['images']:
                    # print(f'image: {image['filename']} generated in C:\softs\ComfyUI\output')
                    image_data = self.get_image(image['filename'], image['subfolder'], image['type'])
                    images_output.append(image_data)
            output_images[node_id] = images_output

        return output_images

    def update_workflow_with_text(self, pos, text):
        self.workflow[f"{pos}"]["inputs"]["text"] = text

    def run_prompts(self, prompts, size=(400,400), im_number=1, shift=3.10, steps=30, cfg=5):
        """
            prompts format: [(positive prompt, negative prompt), ...]
            size: (width, height) of the generated image
            im_number: number of images to generate
            shift: Increase the shift if you get too many blury/dark/bad images. Decrease if you want to try increasing detail. def: 3.10
            steps: number of steps for the diffusion process
            cfg: Set cfg to 1.0 for a speed boost at the cost of consistency. Samplers like res_multistep work pretty well at cfg 1.0.
                The official number of steps is 50 but I think that's too much. Even just 10 steps seems to work.
        """

        self.workflow["58"]["inputs"]["width"] = size[0]
        self.workflow["58"]["inputs"]["height"] = size[1]
        self.workflow["58"]["inputs"]["batch_size"] = im_number
        self.workflow["66"]["inputs"]["shift"] = shift
        self.workflow["3"]["inputs"]["steps"] = steps
        self.workflow["3"]["inputs"]["cfg"] = cfg

        images_out = []
        for prompt_txt in prompts:
            self.workflow["6"]["inputs"]["text"] = prompt_txt[0]
            self.workflow["7"]["inputs"]["text"] = prompt_txt[1]
            
            ws = websocket.WebSocket()
            ws.connect(f"ws://{self.server_address}/ws?clientId={self.client_id}")
            images = self.get_images(ws, self.workflow)
            ws.close()

            for node_id in images:
                for image_data in images[node_id]:
                    image = Image.open(io.BytesIO(image_data))
                    images_out.append(image)

        return images_out

# Example usage:
# client = ArtDesignClient()
# prompts = ["masterpiece best quality man", "a man holding a panel with 'jordy love'"]
# images_list = client.run_prompts(prompts)


class CardLayers:
    """ class to manage card layers """
    def __init__(self):
        self.layers = []

    def round_corners(self, im, radius):
        mask = Image.new('L', im.size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.rounded_rectangle([0, 0, im.width, im.height], radius=radius, fill=255)
        im_rounded = im.copy()
        im_rounded.putalpha(mask)
        return im_rounded

    def rotate_image(self, im, angle, expand=True):
        return im.rotate(angle, expand=expand)

    def white_to_transparent(self, im):
        im_np = np.array(im)
        white_threshold = 200
        white_mask = np.all(im_np[:, :, :3] > white_threshold, axis=2)
        im_np[white_mask, 3] = 0
        return Image.fromarray(im_np)

    def im_resize_scale(self, im, scale_factor):
        new_width = int(im.width * scale_factor)
        new_height = int(im.height * scale_factor)
        new_size = (new_width, new_height)
        return im.resize(new_size, Image.LANCZOS)

    def add_image_overlay(self, base_image, overlay_image_path, position_pct, round_corners_radius=None, white_to_transp=True, resize_scale=None, rotate=0, flip=False):
        """
        position_pct: (x_pct, y_pct) where each is in [0,1] relative to base_image size
        resize_scale: scale factor for overlay image (relative to its original size)
        flip: if True, flip the overlay image horizontally
        """
        overlay_image = Image.open(overlay_image_path).convert('RGBA')
        if white_to_transp:
            overlay_image = self.white_to_transparent(overlay_image)
        if resize_scale:
            overlay_image = self.im_resize_scale(overlay_image, resize_scale)
        if rotate:
            overlay_image = self.rotate_image(overlay_image, rotate)
        if flip:
            overlay_image = overlay_image.transpose(Image.FLIP_LEFT_RIGHT)
        if round_corners_radius:
            overlay_image = self.round_corners(overlay_image, radius=round_corners_radius)
        x = int(base_image.width * position_pct[0])
        y = int(base_image.height * position_pct[1])
        base_image.paste(overlay_image, (x, y), overlay_image)
        return base_image

    def add_text_overlay(self, base_image, text, position_pct, color, font_size_pct=0.1, rotate=0):
        font_size = int(base_image.width * font_size_pct)
        font = ImageFont.truetype(r'..\cards_assets\Aladin-Regular.ttf', size=font_size)
        x = int(base_image.width * position_pct[0])
        y = int(base_image.height * position_pct[1])
        # Measure text size and offset
        dummy_img = Image.new('RGBA', (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)
        text_bbox = dummy_draw.textbbox((0, 0), text, font=font, anchor="mm")
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        # Add padding to avoid cutting
        pad_top = abs(text_bbox[1])
        pad_bottom = max(0, text_bbox[3])
        pad_left = abs(text_bbox[0])
        pad_right = max(0, text_bbox[2])
        padded_w = text_w + pad_left + pad_right
        padded_h = text_h + pad_top + pad_bottom
        text_img = Image.new('RGBA', (padded_w, padded_h), (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_img)
        # Draw text centered in padded image
        text_draw.text(
            (padded_w // 2, padded_h // 2),
            text,
            font=font,
            fill=color,
            anchor="mm"
        )
        if rotate:
            rotated_text = text_img.rotate(rotate, expand=True)
            px = x - rotated_text.width // 2
            py = y - rotated_text.height // 2
            base_image.alpha_composite(rotated_text, dest=(px, py))
        else:
            base_image.alpha_composite(text_img, dest=(x - padded_w // 2, y - padded_h // 2))
        return base_image

    def blur_region(self, im, x_pct, y_pct, w_pct, h_pct, gauss_radius=5, corner_radius_pct=0.1, transp_edge_percent=0.2):
        x = int(im.width * x_pct)
        y = int(im.height * y_pct)
        w = int(im.width * w_pct)
        h = int(im.height * h_pct)
        region = im.crop((x, y, x + w, y + h))
        blurred = region.filter(ImageFilter.GaussianBlur(radius=gauss_radius))
        mask = Image.new('L', (w, h), 0)
        mask_np = np.zeros((h, w), dtype=np.float32)
        edge_x = int(w * transp_edge_percent)
        edge_y = int(h * transp_edge_percent)
        for i in range(h):
            for j in range(w):
                dx = min(j, w - 1 - j)
                dy = min(i, h - 1 - i)
                fx = min(1.0, dx / edge_x) if edge_x > 0 else 1.0
                fy = min(1.0, dy / edge_y) if edge_y > 0 else 1.0
                mask_np[i, j] = fx * fy
        mask_np = (mask_np * 255).astype(np.uint8)
        mask = Image.fromarray(mask_np, mode='L')
        if corner_radius_pct > 0:
            corner_mask = Image.new('L', (w, h), 0)
            draw_mask = ImageDraw.Draw(corner_mask)
            draw_mask.rounded_rectangle([0, 0, w, h], radius=int(im.width * corner_radius_pct), fill=255)
            mask = ImageChops.multiply(mask, corner_mask)
        blended = Image.composite(blurred, region, mask)
        im.paste(blended, (x, y))
        return im

    def color_region(self, im, x_pct, y_pct, w_pct, h_pct, color="#FFFFFF", corner_radius_pct=10, transp_edge_percent=0.2):
        x = int(im.width * x_pct)
        y = int(im.height * y_pct)
        w = int(im.width * w_pct)
        h = int(im.height * h_pct)
        overlay = Image.new('RGBA', (w, h), color)
        mask_np = np.zeros((h, w), dtype=np.float32)
        edge_x = int(w * transp_edge_percent)
        edge_y = int(h * transp_edge_percent)
        for i in range(h):
            for j in range(w):
                dx = min(j, w - 1 - j)
                dy = min(i, h - 1 - i)
                fx = min(1.0, dx / edge_x) if edge_x > 0 else 1.0
                fy = min(1.0, dy / edge_y) if edge_y > 0 else 1.0
                mask_np[i, j] = fx * fy
        mask_np = (mask_np * 255).astype(np.uint8)
        mask = Image.fromarray(mask_np, mode='L')
        if corner_radius_pct > 0:
            corner_mask = Image.new('L', (w, h), 0)
            draw_mask = ImageDraw.Draw(corner_mask)
            draw_mask.rounded_rectangle([0, 0, w, h], radius=int(im.width * corner_radius_pct), fill=255)
            mask = ImageChops.multiply(mask, corner_mask)
        region = im.crop((x, y, x + w, y + h))
        blended = Image.composite(overlay, region, mask)
        im.paste(blended, (x, y))
        return im

    def transparent_colored_overlay(self, im, x_pct, y_pct, w_pct, h_pct, transparency_percent=20, color=(255, 255, 255), corner_radius_pct=0):
        """
        Adds a semi-transparent, colored overlay of a specified size to an image, with optional rounded corners.

        Args:
            im: PIL.Image.Image, input image
            x_pct, y_pct, w_pct, h_pct: region as percent of image size
            transparency_percent: The transparency percentage (0-100). 0=opaque, 100=fully transparent.
            color: The RGB or RGBA tuple for the color of the overlay.
            corner_radius_pct: percent of image width for rounded corners.
        """
        x = int(im.width * x_pct)
        y = int(im.height * y_pct)
        w = int(im.width * w_pct)
        h = int(im.height * h_pct)

        # Ensure the color tuple is RGB
        if len(color) == 4:
            color = color[:3]
        if len(color) != 3:
            print("Error: The 'color' argument must be an RGB tuple (e.g., (255, 0, 0) for red).")
            return

        if not 0 <= transparency_percent <= 100:
            print("Error: Transparency percentage must be between 0 and 100.")
            return

        opacity = 1 - (transparency_percent / 100)
        alpha_value = int(opacity * 255)
        overlay_color = color + (alpha_value,)

        # Create the smaller transparent overlay
        transparent_layer = Image.new('RGBA', (w, h), overlay_color)

        # Create rounded corners mask if needed
        if corner_radius_pct > 0:
            corner_mask = Image.new('L', (w, h), 0)
            draw_mask = ImageDraw.Draw(corner_mask)
            radius = int(im.width * corner_radius_pct)
            draw_mask.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
            # Apply mask to overlay alpha channel
            overlay_np = np.array(transparent_layer)
            mask_np = np.array(corner_mask)
            overlay_np[..., 3] = (overlay_np[..., 3] * (mask_np / 255)).astype(np.uint8)
            transparent_layer = Image.fromarray(overlay_np, mode='RGBA')

        final_image = im.copy()
        final_image.paste(transparent_layer, (x, y), transparent_layer)

        return final_image

    def add_layer_to_a_card(self, imBase_path, faction, condition, effect):
        """ NOT IMPLEMENTED YET """
        blurring_radius = 12
        imBase = Image.open(imBase_path).convert('RGBA')

        # 0 - colored patches on the base image before blurring it (helping see numbers or markers/icons)
        # imBase = color_region(imBase, 1, 60, 45, 45, color="#DFDFDF", corner_radius=10)
        # imBase = color_triangle(imBase, -210, 400, int(200*1.8), int(120*1.8), color="#000000")

        # 1 - blur first so that the layers comes on top
        imBase = self.blur_region(imBase, 0.01, 0.01, 0.12, 0.23, gauss_radius=blurring_radius, corner_radius_pct=0.02, transp_edge_percent=0.0)   # (w start %, h start %, w %, h %) Blurring for top-left icons
        imBase = self.blur_region(imBase, 0.05, 1-0.20-0.005, 0.90, 0.20, gauss_radius=blurring_radius, corner_radius_pct=0.05, transp_edge_percent=0.0)   # (w start %, h start %, w %, h %) Blurring for Condition / Effect
        imBase = self.blur_region(imBase, 0.5-(0.15/2), 1-0.20-0.01-0.1, 0.15, 0.1, gauss_radius=blurring_radius, corner_radius_pct=0.03, transp_edge_percent=0.0)  # (w start %, h start %, w %, h %) Faction logo

        # 2 - markers & texts
        #   2.1 - Top left markers
        imBase = self.add_image_overlay(imBase, r'lib\artdesign\cards_assets\marker_mana.png', (0.005, 0.01), round_corners_radius=None, white_to_transp=True, resize_scale=0.5)                 # Mana marker
        imBase = self.add_text_overlay(imBase, '2', (0.005+0.065, 0.065), color="#FFFFFF", font_size_pct=0.05)                                                                       # Mana cost
        imBase = self.add_text_overlay(imBase, '+2', (0.005+0.062+0.003, 0.135+0.003), color="#ffcb7d", font_size_pct=0.08)                                                          # Value number shadow
        imBase = self.add_text_overlay(imBase, '+2', (0.005+0.062, 0.135), color="#000000", font_size_pct=0.08)                                                                      # Value number
        imBase = self.add_image_overlay(imBase, r'lib\artdesign\cards_assets\marker_shield.png', (0.005+0.015, 0.162), round_corners_radius=None, white_to_transp=True, resize_scale=0.40, rotate=90)         # shield marker
        imBase = self.add_text_overlay(imBase, '3', (0.073, 0.199), color='white', font_size_pct=0.05, rotate=90)                                                                                  # shield value
        #   2.2 - Faction logo
        imBase = self.add_image_overlay(imBase, r'lib\artdesign\cards_assets\logo_bears.png', (0.425, 0.685), round_corners_radius=None, white_to_transp=False, resize_scale=0.2)                 # Faction marker
        #   2.3 - condition & effect
        imBase = self.add_image_overlay(imBase, r'lib\artdesign\cards_assets\cond_night.png', (0.2, 0.82), round_corners_radius=0.0, white_to_transp=False, resize_scale=0.18)                 # effect
        imBase = self.color_region(imBase, 0.5-(0.005/2), 0.81, 0.005, 0.12, color="#171717", corner_radius_pct=0.0, transp_edge_percent=0.15) # SEPARATOR
        # imBase = add_image_overlay(imBase, r'..\cards_assets\marker_unstoppable.png', (0.6, 0.81), round_corners_radius=None, white_to_transp=False, resize_scale=0.11)                 # effect
        imBase = self.add_image_overlay(imBase, r'lib\artdesign\cards_assets\effect_unstoppable.png', (0.6, 0.81), round_corners_radius=0.0, white_to_transp=False, resize_scale=0.24)                 # effect
        #   2.4 - biomes
        imBase = self.add_image_overlay(imBase, r'lib\artdesign\cards_assets\biome_mountain.png', (0.055, 0.94), round_corners_radius=None, white_to_transp=False, resize_scale=0.1)              # 1st biome
        imBase = self.add_image_overlay(imBase, r'lib\artdesign\cards_assets\biome_jungle.png', (0.868, 0.94), round_corners_radius=None, white_to_transp=False, resize_scale=0.1)              # 1st biome
        #   2.5 - card name banner & card name
        imBase = self.color_region(imBase, ((1-0.73)/2), 1-0.05-0.01, 0.73, 0.05, color="#306E2B", corner_radius_pct=0.03, transp_edge_percent=0.0)    # Black banner -border-  under card name
        imBase = self.color_region(imBase, 0.3/2, 1-0.05-0.01, 0.7, 0.05, color="#000000", corner_radius_pct=0.03, transp_edge_percent=0.0)    # Black banner under card name
        imBase = self.add_text_overlay(imBase, 'Guardian Bear rock', (0.5, 1-0.032), color="#773F29", font_size_pct=0.05)   # card name

        imBase = imBase.resize((816, 1110), Image.LANCZOS)
        # imBase = self.round_corners(imBase, radius=15)   # Round the corners of the final card
        imBase.save('im_layered_result.png')
        # imBase.show()

class Utils:
    """ class with utility functions """
    
    def generate_pdf_from_deck(self, deck):
        """ will output a pdf file with all the cards in the deck (list of cards_ids) """
        # Get the image folder
        cards_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'cards_framed'))
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

        # Add instruction text at the top of the first page
        instruction_text = "Scaling parameter: Fit to Paper Size & NO Duplex printing"
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, page_height - 40, instruction_text)

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
        return pdf_buffer.getvalue()