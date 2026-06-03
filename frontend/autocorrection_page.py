import flet as ft
import base64
import os

def main(page: ft.Page):
    # Main window configuration (Matches the iPhone 16 viewport layout)
    page.title = "Azota AI Results Template"
    page.window_width = 393
    page.window_height = 852
    page.window_resizable = False
    page.bgcolor = "#1C1C1E"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    # --- BASE64 IMAGE LOADER HACK ---
    # We lezen de afbeelding binair in en zetten hem om naar een string die de browser direct begrijpt
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        local_img_path = os.path.join(current_dir, "img", "autocorrection_img.png")
        
        with open(local_img_path, "rb") as image_file:
            base64_string = base64.b64encode(image_file.read()).decode('utf-8')
            # Dit is de magische URL die Flet dwingt de afbeelding direct te renderen
            final_image_source = f"data:image/png;base64,{base64_string}"
    except Exception as e:
        # Fallback als er iets misgaat met het bestand vinden
        final_image_source = None
        print(f"Error loading image: {e}")

    # 1. Top Navigation Bar Template
    top_bar = ft.Container(
        width=393, height=75, bgcolor="#D9D9D9",
        content=ft.Row([
            ft.Container(width=15),
            ft.Icon(ft.Icons.CHEVRON_LEFT_ROUNDED, color="black", size=38),
            ft.Container(expand=True),
            ft.Text("Grading Results", color="black", size=18, weight=ft.FontWeight.W_500),
            ft.Container(expand=True),
            ft.Container(width=45),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
    )

    # 2. Pure Image Container
    image_canvas = ft.Container(
        width=350, 
        height=480, 
        bgcolor="white", 
        alignment=ft.Alignment(0, 0),
        # We geven de base64 string mee aan Flet
        content=ft.Image(src=final_image_source, fit="contain") if final_image_source else ft.Text("Afbeelding niet gevonden", color="red")
    )

    # 3. Main Body Configuration
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

    # 4. Footer Button Template
    buttons_area = ft.Container(
        width=393,
        content=ft.Column([
            ft.GestureDetector(
                on_tap=lambda e: print("Reset template triggered"),
                content=ft.Container(
                    width=300, height=45, bgcolor="#1C1C1E", border_radius=22, alignment=ft.Alignment(0, 0),
                    content=ft.Text("Scan New Sheet", color="white", size=16, weight=ft.FontWeight.W_500)
                )
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

    # Render the standalone Results view template
    results_view = ft.Container(
        width=393, height=852, bgcolor="#FFFFFF", border_radius=0,
        content=ft.Column([
            top_bar,
            content_area,
            ft.Container(height=20),
            buttons_area
        ], spacing=0)
    )

    page.add(results_view)

# Start de webserver op de normale manier op (zonder rare assets parameters)
ft.run(main)