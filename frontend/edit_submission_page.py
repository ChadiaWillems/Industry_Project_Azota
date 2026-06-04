import base64
import os
import flet as ft
import style as s

def EditSubmissionView(on_back_click):
    mock_questions = [
        {"id": 1, "answers": {"A": None, "B": s.COLOR_SUCCESS, "C": None, "D": None}},
        {"id": 2, "answers": {"A": None, "B": None, "C": s.COLOR_SUCCESS, "D": None}},
        {"id": 3, "answers": {"A": s.COLOR_FAIL, "B": None, "C": None, "D": None}},
        {"id": 4, "answers": {"A": None, "B": None, "C": None, "D": s.COLOR_SUCCESS}},
        {"id": 5, "answers": {"A": None, "B": s.COLOR_SUCCESS, "C": None, "D": None}},
        {"id": 6, "answers": {"A": s.COLOR_SUCCESS, "B": None, "C": None, "D": None}},
        {"id": 7, "answers": {"A": None, "B": None, "C": s.COLOR_SUCCESS, "D": None}},
        {"id": 8, "answers": {"A": None, "B": None, "C": s.COLOR_FAIL, "D": None}},
        {"id": 9, "answers": {"A": None, "B": None, "C": None, "D": s.COLOR_SUCCESS}},
        {"id": 10, "answers": {"A": None, "B": None, "C": s.COLOR_SUCCESS, "D": None}},
        {"id": 11, "answers": {"A": None, "B": None, "C": None, "D": s.COLOR_SUCCESS}},
        {"id": 12, "answers": {"A": None, "B": None, "C": s.COLOR_SUCCESS, "D": None}},
        {"id": 13, "answers": {"A": None, "B": s.COLOR_SUCCESS, "C": None, "D": None}},
        {"id": 14, "answers": {"A": None, "B": None, "C": s.COLOR_SUCCESS, "D": None}},
        {"id": 15, "answers": {"A": None, "B": None, "C": None, "D": s.COLOR_SUCCESS}},
    ]

    score_text = ft.Text("10/15", color=s.COLOR_SECONDARY, size=18, weight=ft.FontWeight.W_500)

    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        local_logo_path = os.path.join(current_dir, "img", "Azota_logo.png")
        
        with open(local_logo_path, "rb") as logo_file:
            base64_logo = base64.b64encode(logo_file.read()).decode('utf-8')
            final_logo_source = f"data:image/png;base64,{base64_logo}"
    except Exception as e:
        final_logo_source = None
        print(f"Error loading image: {e}")

    def update_live_score():
        correct_count = 0
        for q in mock_questions:
            for letter in ["A", "B", "C", "D"]:
                if q["answers"][letter] == s.COLOR_SUCCESS or q["answers"][letter] == "green":
                    correct_count += 1
        score_text.value = f"{correct_count}/15"
        score_text.update()

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
                
                ft.Text("Edit Grading Results", color=s.COLOR_SECONDARY, size=18, weight=ft.FontWeight.BOLD),
                
                ft.Container(expand=True),
            
                ft.Container(
                    width=28, height=28,
                    content=ft.Image(src=final_logo_source, fit="contain") if final_logo_source else ft.Icon(ft.Icons.CHANGE_HISTORY_ROUNDED, color=s.COLOR_PRIMARY, size=26)
                ),
                
                ft.Container(width=15),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
        )

    student_info = ft.Container(
        padding=ft.Padding.symmetric(horizontal=25, vertical=15),
        content=ft.Row([
            ft.Text("Student name", color=s.COLOR_SECONDARY, size=18, weight=ft.FontWeight.W_500),
            score_text
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    )

    def on_bubble_click(q_id, letter, container_widget):
        for q in mock_questions:
            if q["id"] == q_id:
                current_status = q["answers"][letter]
                
                if current_status is None:
                    new_status = s.COLOR_SUCCESS
                elif current_status == s.COLOR_SUCCESS or current_status == "green":
                    new_status = s.COLOR_FAIL
                else:
                    new_status = None
                
                for l in ["A", "B", "C", "D"]:
                    q["answers"][l] = None
                
                q["answers"][letter] = new_status
                
                phan1_column.controls = [build_bubble_row(question["id"], question["answers"]) for question in mock_questions]
                phan1_column.update()
                
                update_live_score()
                break

    def build_bubble_row(q_id, answers):
        bubbles = []
        for letter in ["A", "B", "C", "D"]:
            status = answers[letter]
            bg_color = "transparent" if status is None else status
            text_color = s.COLOR_SECONDARY if status is None else s.COLOR_CARD_WHITE
            border_color = s.COLOR_SECONDARY if status is None else "transparent"
          
            bubble_container = ft.Container(
                width=26, height=26, border_radius=13, bgcolor=bg_color,
                border=ft.Border.all(1, border_color) if border_color != "transparent" else None,
                alignment=ft.Alignment(0, 0),
                content=ft.Text(letter, color=text_color, size=12, weight=ft.FontWeight.BOLD)
            )
            
            bubbles.append(
                ft.GestureDetector(
                    on_tap=lambda e, q=q_id, l=letter, c=bubble_container: on_bubble_click(q, l, c),
                    content=bubble_container
                )
            )
            
        return ft.Row([
            ft.Container(content=ft.Text(f"{q_id}:", color=s.COLOR_SECONDARY, size=14, weight=ft.FontWeight.W_500), width=30),
            ft.Row(bubbles, spacing=8)
        ], alignment=ft.MainAxisAlignment.START)

    phan1_column = ft.Column(
        [build_bubble_row(q["id"], q["answers"]) for q in mock_questions],
        spacing=10
    )

    phan1_content = ft.Container(
        content=phan1_column,
        padding=ft.Padding.only(left=20, bottom=15)
    )

    accordion_lists = ft.Container(
        width=393,
        height=650, 
        content=ft.ListView([
            # Sectie 1
            ft.Container(
                border=ft.Border(bottom=ft.BorderSide(1, s.COLOR_BORDER)),
                theme=ft.Theme(divider_color="transparent"),
                content=ft.ExpansionTile(
                    title=ft.Text("Phan 1", color=s.COLOR_SECONDARY, weight=ft.FontWeight.BOLD), 
                    expanded=True,
                    controls=[phan1_content]
                )
            ),
            # Sectie 2
            ft.Container(
                border=ft.Border(bottom=ft.BorderSide(1, s.COLOR_BORDER)),
                theme=ft.Theme(divider_color="transparent"),
                content=ft.ExpansionTile(
                    title=ft.Text("Phan 2", color=s.COLOR_SECONDARY, weight=ft.FontWeight.BOLD), 
                    controls=[ft.Text("No questions", color=s.COLOR_GRAY_TEXT)]
                )
            ),
            # Sectie 3
            ft.Container(
                border=ft.Border(bottom=ft.BorderSide(1, s.COLOR_BORDER)),
                theme=ft.Theme(divider_color="transparent"),
                content=ft.ExpansionTile(
                    title=ft.Text("Phan 3", color=s.COLOR_SECONDARY, weight=ft.FontWeight.BOLD), 
                    controls=[ft.Text("No questions", color=s.COLOR_GRAY_TEXT)]
                )
            ),
        ])
    )

    save_button_area = ft.Container(
        width=393, padding=ft.Padding.only(bottom=20),
        content=ft.Column([
            ft.GestureDetector(
                on_tap=on_back_click, 
                content=ft.Container(
                    width=340, 
                    height=48,
                    bgcolor=s.COLOR_PRIMARY,
                    border_radius=24,
                    alignment=ft.Alignment(0, 0),
                    shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color="#302361AE"),
                    content=ft.Text(
                        "Save Changes", 
                        color="white",
                        size=16, 
                        weight=ft.FontWeight.BOLD,
                        font_family=s.FONT_FAMILY
                    )
                )
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

    return ft.Container(width=393, height=852, bgcolor=s.COLOR_BG_LIGHT, content=ft.Column([top_bar, student_info, accordion_lists, ft.Container(expand=True), save_button_area], spacing=0))