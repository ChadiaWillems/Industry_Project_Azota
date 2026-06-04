# app.py
import flet as ft
from uploading_picture_page import CameraView
from autocorrection_page import ResultsView
from edit_submission_page import EditSubmissionView
import style as s  

def main(page: ft.Page):
    page.title = "Azota AI Production App"
    page.window_width = 393
    page.window_height = 852
    page.window_resizable = False
    page.bgcolor = s.COLOR_SECONDARY 
    
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    file_picker = ft.FilePicker()

    main_container = ft.Container(width=393, height=852, bgcolor=s.COLOR_BG_LIGHT)

    def go_to_camera():
        main_container.content = CameraView(
            page=page,
            file_picker=file_picker, # Geef de picker mee
            on_submit_click=lambda _: go_to_results()
        )
        main_container.update()

    def go_to_results():
        main_container.content = ResultsView(
            on_edit_click=lambda _: go_to_edit(),
            on_back_click=lambda _: go_to_camera() 
        )
        main_container.update()

    def go_to_edit():
        main_container.content = EditSubmissionView(
            on_back_click=lambda _: go_to_camera()
        )
        main_container.update()

    page.add(file_picker, main_container)
    go_to_camera()

if __name__ == "__main__":
    ft.run(main, host="0.0.0.0", port=8555)