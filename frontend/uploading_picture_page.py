import flet as ft

def main(page: ft.Page):
    # Main window configuration
    page.title = "iPhone 16 Multi-page UI"
    page.window_width = 393
    page.window_height = 852
    page.window_resizable = False
    page.bgcolor = "#1C1C1E"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    main_container = ft.Container(width=393, height=852)

    # Selected image
    #selected_image_path = [r"d:\Dowloads\template 1\ALL mau\V22\ß║ónh 1.jpg"]
    selected_image_path = [None]

    # System file picker
    def on_pick_file_result(e):
        if e.files and e.files[0].path:
            selected_image_path[0] = e.files[0].path
            Switch_to_preview(None)

    file_picker = ft.FilePicker()
    file_picker.on_result = on_pick_file_result
    page.overlay.append(file_picker)


    # ==========================================
    # Screen 1: Camera
    # ==========================================
    def Camera():
        # Top bar
        top_controls=ft.Container(
            width=393, height=75, bgcolor="#D9D9D9"
        )
        
        # Creating a default viewfinder (When camera is turned off)
        viewfinder = ft.Container(
            width=393, height=757, bgcolor="#FFFFFF", border_radius=0,
            alignment=ft.Alignment(0, 0),
            content=ft.Text("Camera is turned off\nPress the gallery button or the capture button", 
                            color="#555555", text_align=ft.TextAlign.CENTER, size=14)
        )
        # If the user picks or captures an image, it will be displayed
        if selected_image_path[0]:
            viewfinder.content = ft.Image(src=selected_image_path[0], width=393, height=757, fit=ft.ImageFit.COVER, border_radius=48)

        # Capture trigger button
        def trigger_capture(e):
            file_picker.pick_files(allow_multiple=False, type=ft.FilePickerFileType.IMAGE)


        # Bottom bar
        bottom_controls = ft.Container(
            width=393, height=181, bottom=20, bgcolor="#D9D9D9",
            content=ft.Column([
                ft.Container(height=15),
                ft.Row([
                    ft.Container(width=63),
                    ft.GestureDetector(
                        on_tap=trigger_capture,
                        content=ft.Container(
                            width=76, height=76, bgcolor="#D9D9D9", border_radius=38, alignment=ft.Alignment(0, 0),
                            content=ft.Container(width=66, height=66, bgcolor="black", border_radius=33, alignment=ft.Alignment(0, 0),
                                content=ft.Container(width=54, height=54, bgcolor="white", border_radius=27)
                            )
                        )
                    ),
                    ft.Container(
                        width=63, height=84, bgcolor="#2C2C2E", border_radius=0, 
                        alignment=ft.Alignment(0, 0),
                        content=ft.Icon(ft.Icons.PHOTO_LIBRARY_OUTLINED, color="white", size=20),
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
        top_controls = ft.Container(
            width=393,
            content=ft.Column([
                ft.Container(
                    width=393,
                    height=75, 
                    bgcolor="#D9D9D9", 
                    content=ft.Row([
                        ft.Container(width=15), 
                        ft.GestureDetector(
                            on_tap=Switch_to_camera, 
                            content=ft.Icon(ft.Icons.CHEVRON_LEFT_ROUNDED, color="black", size=38)
                        )
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
                )
            ], spacing=0) 
        )

        custom_button = ft.Container(
            width=220,
            height=50,
            bgcolor="#0A84FF", 
            border_radius=12,
            alignment=ft.Alignment(0, 0),
            content=ft.Text("Pick one picture", color="white", weight=ft.FontWeight.BOLD, size=14),
            on_click=lambda e: file_picker.pick_files()
        )

        album_placeholder = ft.Container(
            width=393, height=777, bgcolor="#FFFFFF", border_radius=0,
            alignment=ft.Alignment(-1, 0),
            content=ft.Column([
                ft.Icon(ft.Icons.IMAGE_SEARCH_ROUNDED, color="#444444", size=60),
                ft.Text("Album", color="#888888", size=14),
                ft.Container(height=30),
                custom_button 
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )

        return ft.Container(
            width=393, height=852, bgcolor="#070707", border_radius=0, 
            content=ft.Stack([
                top_controls,
                ft.Row([album_placeholder], alignment=ft.MainAxisAlignment.CENTER, top=75, width=393) 
            ])
        )


    # ==========================================
    # Screen 3: Preview
    # ==========================================
    def Preview():
        # 1. Top bar
        top_bar = ft.Container(
            width=393, height=75, bgcolor="#D9D9D9",
            content=ft.Row([
                ft.Container(width=15),
                ft.Icon(ft.Icons.CHEVRON_LEFT_ROUNDED, color="black", size=38), 
                ft.Container(expand=True),
                ft.Text("Preview submission", color="black", size=18, weight=ft.FontWeight.W_500),
                ft.Container(expand=True), 
                ft.Container(width=45),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
        )

        # 2. Image border
        image_preview_box = ft.Container(
            width=350, height=480, bgcolor="#0A84FF", alignment=ft.Alignment(0, 0),
            content=ft.Container(
                width=344, height=474, bgcolor="white", alignment=ft.Alignment(0, 0),
                content=ft.Image(src=selected_image_path[0], fit="contain") if selected_image_path[0] else ft.Container()
            )
        )

        # 3. Main content (Name, note, image)
        content_area = ft.Container(
            width=393,
            content=ft.Column([
                ft.Container(height=30),
                ft.Row([
                    ft.Container(width=30),
                    ft.Text("Name:", color="black", size=14),
                    ft.Container(width=20),
                    ft.Text("Student name", color="black", size=14, weight=ft.FontWeight.W_500)
                ]),
                ft.Container(height=20),
                ft.Row([
                    ft.Container(width=25),
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color="black", size=16),
                    ft.Text("Make sure all answers are clearly legible before\nsubmitting.", color="black", size=12)
                ], vertical_alignment=ft.CrossAxisAlignment.START),
                ft.Container(height=10),
                ft.Row([image_preview_box], alignment=ft.MainAxisAlignment.CENTER) 
            ], spacing=0)
        )

        # Retake func
        def Retake_button(e):
            selected_image_path[0] = None 
            Switch_to_camera(None)      

        # 4. Retake button and Submit button
        buttons_area = ft.Container(
            width=393,
            content=ft.Column([
                ft.GestureDetector(
                    on_tap=Retake_button,
                    content=ft.Container(
                        width=300, height=45, bgcolor="#D9D9D9", border_radius=22, alignment=ft.Alignment(0, 0),
                        content=ft.Text("Retake picture", color="black", size=16)
                    )
                ),
                ft.Container(height=15),
                ft.Container(
                    width=300, height=45, bgcolor="#D9D9D9", border_radius=22, alignment=ft.Alignment(0, 0),
                    content=ft.Text("Submit assignment", color="black", size=16)
                ) 
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )


        return ft.Container(
            width=393, height=852, bgcolor="#FFFFFF", border_radius=0,
            content=ft.Column([
                top_bar,
                content_area,
                ft.Container(height=15),
                buttons_area
            ], spacing=0)
        )


    # ==========================================
    # functions for switching
    # ==========================================
    def Switch_to_camera(e):
        main_container.content = Camera() 
        main_container.update()

    def Switch_to_gallery(e):
        main_container.content = Gallery() 
        main_container.update()

    def Switch_to_preview(e):
        main_container.content = Preview() 
        main_container.update()


    # --- Activating app ---
    #main_container.content = Preview()
    #page.add(main_container)
    main_container.content = Camera()
    page.add(main_container)

ft.app(target=main)