# autocorrection_page.py
import flet as ft
import base64
import os
import style as s

def ResultsView(on_edit_click, on_back_click):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        local_img_path = os.path.join(current_dir, "img", "autocorrection_img.png")
        local_logo_path = os.path.join(current_dir, "img", "Azota_logo.png")
        
        with open(local_img_path, "rb") as image_file:
            base64_string = base64.b64encode(image_file.read()).decode('utf-8')
            final_image_source = f"data:image/png;base64,{base64_string}"
        
        with open(local_logo_path, "rb") as logo_file:
            base64_logo = base64.b64encode(logo_file.read()).decode('utf-8')
            final_logo_source = f"data:image/png;base64,{base64_logo}"

    except Exception as e:
        final_image_source = None
        final_logo_source = None
        print(f"Error loading image: {e}")

    top_bar = ft.Container(
        width=393, height=70, bgcolor=s.COLOR_CARD_WHITE,
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=10, color="#0A000000"),
        content=ft.Row([
            ft.Container(width=15),
            
            ft.GestureDetector(
                on_tap=on_back_click,
                content=ft.Icon(ft.Icons.CHEVRON_LEFT_ROUNDED, color=s.COLOR_PRIMARY, size=32)
            ),
            
            ft.Container(expand=True),
            
            ft.Text("Grading Results", color=s.COLOR_SECONDARY, size=18, weight=ft.FontWeight.BOLD),
            
            ft.Container(expand=True),
        
            ft.Container(
                width=28, height=28,
                content=ft.Image(src=final_logo_source, fit="contain") if final_logo_source else ft.Icon(ft.Icons.CHANGE_HISTORY_ROUNDED, color=s.COLOR_PRIMARY, size=26)
            ),
            
            ft.Container(width=15),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
    )

    image_canvas = ft.Container(
        width=350, 
        height=480, 
        bgcolor="white", 
        alignment=ft.Alignment(0, 0),
        content=ft.Image(src=final_image_source, fit="contain") if final_image_source else ft.Text("Afbeelding niet gevonden", color="red")
    )

    content_area = ft.Container(
        width=393,
        content=ft.Column([
            ft.Container(height=25),
            ft.Row([
                ft.Text("Evaluation Finished", color="black", size=22, weight=ft.FontWeight.BOLD),
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=10),
            ft.Row([
                ft.Container(
                    content=ft.Text("Score: 12 / 15", size=16, weight=ft.FontWeight.BOLD, color="white"),
                    bgcolor="green", 
                    padding=ft.Padding.symmetric(horizontal=20, vertical=8), 
                    border_radius=15
                )
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=20),
            ft.Row([image_canvas], alignment=ft.MainAxisAlignment.CENTER)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

    buttons_area = ft.Container(
        width=393,
        content=ft.Row([
            ft.GestureDetector(
                on_tap=on_edit_click,
                content=ft.Container(
                    width=145, 
                    height=45, 
                    bgcolor="transparent",
                    border=ft.Border.all(2, s.COLOR_PRIMARY), 
                    border_radius=22, 
                    alignment=ft.Alignment(0, 0),
                    content=ft.Text(
                        "Edit Image", 
                        color=s.COLOR_PRIMARY, 
                        size=15, 
                        weight=ft.FontWeight.BOLD,
                        font_family=s.FONT_FAMILY
                    )
                )
            ),
            
            
            ft.GestureDetector(
                on_tap=lambda e: print("Save button clicked"),
                content=ft.Container(
                    width=145, 
                    height=45, 
                    bgcolor=s.COLOR_PRIMARY,
                    border_radius=22, 
                    alignment=ft.Alignment(0, 0),
                    shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color="#302361AE"),
                    content=ft.Text(
                        "Save Image", 
                        color="white",
                        size=15, 
                        weight=ft.FontWeight.BOLD,
                        font_family=s.FONT_FAMILY
                    )
                )
            )
        ], alignment=ft.MainAxisAlignment.SPACE_EVENLY)
    )

    return ft.Container(
        width=393, height=852, bgcolor=s.COLOR_BG_LIGHT, border_radius=0,
        content=ft.Column([
            top_bar,
            content_area,
            ft.Container(height=20),
            buttons_area
        ], spacing=0)
    )