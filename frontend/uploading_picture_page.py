import base64
import os
import flet as ft
import style as s

def CameraView(page: ft.Page, file_picker: ft.FilePicker, on_submit_click):
    sub_container = ft.Container(width=393, height=852)

    selected_image_path = [None]

    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        local_logo_full_path = os.path.join(current_dir, "img", "Azota_logo_full.png")
        local_logo_simple_path = os.path.join(current_dir, "img", "Azota_logo.png")
        local_img_path = os.path.join(current_dir, "img", "scan00011.png")
        
        with open(local_logo_full_path, "rb") as logo_file:
            base64_logo = base64.b64encode(logo_file.read()).decode('utf-8')
            final_logo_source = f"data:image/png;base64,{base64_logo}"
        with open(local_logo_simple_path, "rb") as logo_file:
            base64_logo = base64.b64encode(logo_file.read()).decode('utf-8')
            final_logo_source_simple = f"data:image/png;base64,{base64_logo}"
        with open(local_img_path, "rb") as image_file:
            base64_string = base64.b64encode(image_file.read()).decode('utf-8')
            final_image_source = f"data:image/png;base64,{base64_string}"
    except Exception as e:
        final_logo_source = None
        final_logo_source_simple = None
        final_image_source = None
        print(f"Error loading logo in camera page: {e}")

    def on_pick_file_result(e):
        if e.files and e.files[0].path:
            selected_image_path[0] = e.files[0].path
            Switch_to_preview(None)

    file_picker.on_result = on_pick_file_result

    # ==========================================
    # Screen 1: Camera
    # ==========================================
    def Camera():
        top_controls = ft.Container(
            width=393, 
            height=90,
            bgcolor=s.COLOR_CARD_WHITE,
            alignment=ft.Alignment(0, 0),
            content=ft.Image(
                src=final_logo_source,
                width=130,
                height=40,
                fit="contain"
            ) if final_logo_source else ft.Icon(ft.Icons.CHANGE_HISTORY_ROUNDED, color=s.COLOR_PRIMARY, size=35)
        )
        
        viewfinder = ft.Container(
            width=393, height=757, bgcolor=s.COLOR_BG_LIGHT, border_radius=0,
            alignment=ft.Alignment(0, 0),
            content=ft.Text("Camera is turned off\nPress the gallery button or the capture button", 
                            color=s.COLOR_SECONDARY, text_align=ft.TextAlign.CENTER, size=14)
        )

        if selected_image_path[0]:
            viewfinder.content = ft.Image(src=selected_image_path[0], width=393, height=757, fit=ft.ImageFit.COVER, border_radius=48)

        def trigger_capture(e):
            Switch_to_preview(None)

        bottom_controls = ft.Container(
            width=393, height=150, bottom=10, bgcolor=s.COLOR_CARD_WHITE,
            content=ft.Column([
                ft.Container(height=15),
                ft.Row([
                    ft.Container(width=63),
                    ft.GestureDetector(
                        on_tap=trigger_capture,
                        content=ft.Container(
                            width=60, height=60, bgcolor=s.COLOR_PRIMARY, border_radius=38, alignment=ft.Alignment(0, 0),
                            content=ft.Container(width=50, height=50, bgcolor=s.COLOR_CARD_WHITE, border_radius=33, alignment=ft.Alignment(0, 0),
                                content=ft.Container(width=50, height=50, bgcolor=s.COLOR_CARD_WHITE, border_radius=27)
                            )
                        )
                    ),
                    ft.Container(
                        width=63, height=84, bgcolor=s.COLOR_SECONDARY, border_radius=0, 
                        alignment=ft.Alignment(0, 0),
                        content=ft.Icon(ft.Icons.PHOTO_LIBRARY_OUTLINED, color=s.COLOR_CARD_WHITE, size=20),
                        on_click=Switch_to_gallery
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )

        return ft.Container(
            width=393, height=852, border_radius=0,
            content=ft.Stack([
                viewfinder,
                top_controls,
                bottom_controls
            ])
        )

    # ==========================================
    # Screen 2: Gallery
    # ==========================================
    def Gallery():
        # Top bar
        top_bar = ft.Container(
            width=393, 
            height=70, 
            bgcolor=s.COLOR_CARD_WHITE, 
            content=ft.Row([
                ft.Container(width=15),
                
                ft.GestureDetector(
                    on_tap=Switch_to_camera,
                    content=ft.Icon(ft.Icons.CHEVRON_LEFT_ROUNDED, color=s.COLOR_PRIMARY, size=32)
                ),
                
                ft.Container(expand=True),
                
                ft.Text("Pick picture", color=s.COLOR_SECONDARY, size=18, weight=ft.FontWeight.BOLD),
                
                ft.Container(expand=True),
            
                ft.Container(
                    width=28, height=28,
                    content=ft.Image(src=final_logo_source_simple, fit="contain") if final_logo_source else ft.Icon(ft.Icons.CHANGE_HISTORY_ROUNDED, color=s.COLOR_PRIMARY, size=26)
                ),
                
                ft.Container(width=15),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
        )

        custom_button = ft.Container(
            width=220,
            height=50,
            bgcolor=s.COLOR_PRIMARY, 
            border_radius=12,
            alignment=ft.Alignment(0, 0),
            content=ft.Text("Pick one picture", color="white", weight=ft.FontWeight.BOLD, size=14),
            on_click=lambda e: file_picker.pick_files()
        )

        album_placeholder = ft.Container(
            width=393, height=777, bgcolor="#FFFFFF", border_radius=0,
            alignment=ft.Alignment(-1, 0),
            content=ft.Column([
                ft.Icon(ft.Icons.IMAGE_SEARCH_ROUNDED, color=s.COLOR_SECONDARY, size=60),
                ft.Text("Album", color=s.COLOR_SECONDARY, size=14),
                ft.Container(height=30),
                custom_button 
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )

        return ft.Container(
            width=393, height=852, bgcolor=s.COLOR_CARD_WHITE, border_radius=0, 
            content=ft.Stack([
                top_bar,
                ft.Row([album_placeholder], alignment=ft.MainAxisAlignment.CENTER, top=75, width=393) 
            ])
        )

    # ==========================================
    # Screen 3: Preview
    # ==========================================
    def Preview():

        top_bar = ft.Container(
            width=393, 
            height=70, 
            bgcolor=s.COLOR_CARD_WHITE, 
            content=ft.Row([
                ft.Container(width=15),
                
                ft.GestureDetector(
                    on_tap=Switch_to_camera,
                    content=ft.Icon(ft.Icons.CHEVRON_LEFT_ROUNDED, color=s.COLOR_PRIMARY, size=32)
                ),
                
                ft.Container(expand=True),
                
                ft.Text("Preview Submission", color=s.COLOR_SECONDARY, size=18, weight=ft.FontWeight.BOLD),
                
                ft.Container(expand=True),
            
                ft.Container(
                    width=28, height=28,
                    content=ft.Image(src=final_logo_source_simple, fit="contain") if final_logo_source else ft.Icon(ft.Icons.CHANGE_HISTORY_ROUNDED, color=s.COLOR_PRIMARY, size=26)
                ),
                
                ft.Container(width=15),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
        )

        image_preview_box = ft.Container(
            width=350, 
            height=460, 
            bgcolor=s.COLOR_CARD_WHITE, 
            border_radius=16,
            padding=8,
            alignment=ft.Alignment(0, 0),
            content=ft.Image(
                src=selected_image_path[0] if selected_image_path[0] else final_image_source, 
                fit="contain"
            ) if (selected_image_path[0] or final_image_source) else ft.Text("No image data available", color="red")
        )

        content_area = ft.Container(
            width=393,
            content=ft.Column([
                ft.Container(height=30),
                ft.Row([
                    ft.Container(width=30),
                    ft.Text("Name:", color=s.COLOR_SECONDARY, size=14),
                    ft.Container(width=20),
                    ft.Text("Student name", color=s.COLOR_SECONDARY, size=14, weight=ft.FontWeight.W_500)
                ]),
                ft.Container(height=20),
                ft.Row([
                    ft.Container(width=25),
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color=s.COLOR_SECONDARY, size=16),
                    ft.Text("Make sure all answers are clearly legible before\nsubmitting.", color=s.COLOR_SECONDARY, size=12)
                ], vertical_alignment=ft.CrossAxisAlignment.START),
                ft.Container(height=10),
                ft.Row([image_preview_box], alignment=ft.MainAxisAlignment.CENTER) 
            ], spacing=0)
        )

        def Retake_button(e):
            selected_image_path[0] = None 
            Switch_to_camera(None)      

        buttons_area = ft.Container(
            width=393,
            content=ft.Row([
                ft.GestureDetector(
                    on_tap=Retake_button,
                    content=ft.Container(
                        width=160,
                        height=46, 
                        bgcolor="transparent",
                        border=ft.Border.all(2, s.COLOR_PRIMARY),
                        border_radius=23, 
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text(
                            "Retake", 
                            color=s.COLOR_PRIMARY, 
                            size=15, 
                            weight=ft.FontWeight.BOLD,
                            font_family=s.FONT_FAMILY
                        )
                    )
                ),
                
                ft.GestureDetector(
                    on_tap=on_submit_click,
                    content=ft.Container(
                        width=160,
                        height=46, 
                        bgcolor=s.COLOR_PRIMARY, 
                        border_radius=23, 
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text(
                            "Submit", 
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
            width=393, 
            height=852, 
            bgcolor=s.COLOR_CARD_WHITE, 
            border_radius=0,
            content=ft.Column([
                top_bar,
                content_area,
                ft.Container(expand=True), 
                
                ft.Container(
                    content=buttons_area,
                    padding=ft.Padding.only(bottom=75)
                )
            ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )

    # ==========================================
    # functions for switching (Local inside View)
    # ==========================================
    def Switch_to_camera(e):
        sub_container.content = Camera() 
        sub_container.update()

    def Switch_to_gallery(e):
        sub_container.content = Gallery() 
        sub_container.update()

    def Switch_to_preview(e):
        sub_container.content = Preview() 
        sub_container.update()

    sub_container.content = Camera()
    return sub_container