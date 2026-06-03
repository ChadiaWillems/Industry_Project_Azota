import flet as ft

def EditSubmissionView(on_back_click):
    # Mock data specifiek voor de vragenlijst
    mock_questions = [
        {"id": 1, "answers": {"A": None, "B": "green", "C": None, "D": None}},
        {"id": 2, "answers": {"A": None, "B": None, "C": "green", "D": None}},
        {"id": 3, "answers": {"A": "red", "B": None, "C": None, "D": None}},
        {"id": 4, "answers": {"A": None, "B": None, "C": None, "D": "green"}},
        {"id": 5, "answers": {"A": None, "B": "green", "C": None, "D": None}},
        {"id": 6, "answers": {"A": "green", "B": None, "C": None, "D": None}},
        {"id": 7, "answers": {"A": None, "B": None, "C": "green", "D": None}},
        {"id": 8, "answers": {"A": None, "B": None, "C": "red", "D": None}},
        {"id": 9, "answers": {"A": None, "B": None, "C": None, "D": "green"}},
        {"id": 10, "answers": {"A": None, "B": None, "C": "green", "D": None}},
        {"id": 11, "answers": {"A": None, "B": None, "C": None, "D": "green"}},
        {"id": 12, "answers": {"A": None, "B": None, "C": None, "D": "green"}},
        {"id": 13, "answers": {"A": None, "B": "green", "C": None, "D": None}},
        {"id": 14, "answers": {"A": None, "B": None, "C": "green", "D": None}},
        {"id": 15, "answers": {"A": None, "B": None, "C": None, "D": "green"}},
    ]

    top_bar = ft.Container(
        width=393, height=75, bgcolor="#D9D9D9",
        content=ft.Row([
            ft.Container(width=15),
            ft.GestureDetector(
                on_tap=on_back_click, 
                content=ft.Icon(ft.Icons.CHEVRON_LEFT_ROUNDED, color="black", size=38)
            ),
            ft.Container(expand=True),
            ft.Text("Edit submission", color="black", size=18, weight=ft.FontWeight.W_500),
            ft.Container(expand=True),
            ft.Icon(ft.Icons.CHANGE_HISTORY_ROUNDED, color="#0A84FF", size=28),
            ft.Container(width=15),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
    )

    # FIXED: ft.padding -> ft.Padding
    student_info = ft.Container(
        padding=ft.Padding.symmetric(horizontal=25, vertical=15),
        content=ft.Row([
            ft.Text("Student name", color="black", size=18, weight=ft.FontWeight.W_500),
            ft.Text("10/15", color="black", size=18, weight=ft.FontWeight.W_500)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    )

    def build_bubble_row(q_id, answers):
        bubbles = []
        for letter in ["A", "B", "C", "D"]:
            status = answers[letter]
            bg_color = "transparent" if status is None else status
            text_color = "black" if status is None else "white"
            border_color = "black" if status is None else "transparent"
            
            bubbles.append(
                ft.Container(
                    width=26, height=26, border_radius=13, bgcolor=bg_color,
                    border=ft.Border.all(1, border_color) if border_color != "transparent" else None,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Text(letter, color=text_color, size=12, weight=ft.FontWeight.BOLD)
                )
            )
        return ft.Row([
            ft.Container(content=ft.Text(f"{q_id}:", color="black", size=14, weight=ft.FontWeight.W_500), width=30),
            ft.Row(bubbles, spacing=8)
        ], alignment=ft.MainAxisAlignment.START)

    # De Column regelt nu puur de vragen onder elkaar
    phan1_column = ft.Column(
        [build_bubble_row(q["id"], q["answers"]) for q in mock_questions],
        spacing=10
    )

    # De Container vangt de padding op die de Column niet mag hebben
    phan1_content = ft.Container(
        content=phan1_column,
        padding=ft.Padding.only(left=20, bottom=15)
    )

    accordion_lists = ft.Container(
        width=393, height=530,
        content=ft.ListView([
            # FIXED: initially_expanded=True -> expanded=True
            ft.ExpansionTile(
                title=ft.Text("Phan 1", color="black", weight=ft.FontWeight.BOLD), 
                expanded=True, 
                controls=[phan1_content]
            ),
            # FIXED: padding verwijderd uit ft.Text widgets
            ft.ExpansionTile(
                title=ft.Text("Phan 2", color="black", weight=ft.FontWeight.BOLD), 
                controls=[ft.Text("No questions", color="grey")]
            ),
            ft.ExpansionTile(
                title=ft.Text("Phan 3", color="black", weight=ft.FontWeight.BOLD), 
                controls=[ft.Text("No questions", color="grey")]
            ),
        ], expand=True)
    )

    # FIXED: ft.padding -> ft.Padding
    save_button_area = ft.Container(
        width=393, padding=ft.Padding.only(bottom=20),
        content=ft.Column([
            ft.GestureDetector(
                on_tap=on_back_click, 
                content=ft.Container(
                    width=340, height=45, bgcolor="#D9D9D9", border_radius=22, alignment=ft.Alignment(0, 0),
                    content=ft.Text("Save", color="black", size=16, weight=ft.FontWeight.W_500)
                )
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

    return ft.Container(width=393, height=852, bgcolor="#FFFFFF", content=ft.Column([top_bar, student_info, accordion_lists, ft.Container(expand=True), save_button_area], spacing=0))