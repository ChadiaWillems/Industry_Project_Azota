import flet as ft

def EditSubmissionView(on_back_click):
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
        {"id": 12, "answers": {"A": None, "B": None, "C": "green", "D": None}},
        {"id": 13, "answers": {"A": None, "B": "green", "C": None, "D": None}},
        {"id": 14, "answers": {"A": None, "B": None, "C": "green", "D": None}},
        {"id": 15, "answers": {"A": None, "B": None, "C": None, "D": "green"}},
    ]

    score_text = ft.Text("10/15", color="black", size=18, weight=ft.FontWeight.W_500)

    def update_live_score():
        correct_count = 0
        for q in mock_questions:
            for letter in ["A", "B", "C", "D"]:
                if q["answers"][letter] == "green":
                    correct_count += 1
        score_text.value = f"{correct_count}/15"
        score_text.update()

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

    student_info = ft.Container(
        padding=ft.Padding.symmetric(horizontal=25, vertical=15),
        content=ft.Row([
            ft.Text("Student name", color="black", size=18, weight=ft.FontWeight.W_500),
            score_text
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    )

    def on_bubble_click(q_id, letter, container_widget):
        for q in mock_questions:
            if q["id"] == q_id:
                current_status = q["answers"][letter]
                
                if current_status is None:
                    new_status = "green"
                elif current_status == "green":
                    new_status = "red"
                else:
                    new_status = None
                
                q["answers"][letter] = new_status
                
                container_widget.bgcolor = "transparent" if new_status is None else new_status
                container_widget.content.color = "black" if new_status is None else "white"
                container_widget.border = ft.Border.all(1, "black") if new_status is None else None
                container_widget.update()
                
                update_live_score()
                break

    def build_bubble_row(q_id, answers):
        bubbles = []
        for letter in ["A", "B", "C", "D"]:
            status = answers[letter]
            bg_color = "transparent" if status is None else status
            text_color = "black" if status is None else "white"
            border_color = "black" if status is None else "transparent"
          
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
            ft.Container(content=ft.Text(f"{q_id}:", color="black", size=14, weight=ft.FontWeight.W_500), width=30),
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
        height=550, 
        content=ft.ListView([
            # Sectie 1
            ft.Container(
                border=ft.Border(bottom=ft.BorderSide(1, "#D3D3D3")),
                theme=ft.Theme(divider_color="transparent"),
                content=ft.ExpansionTile(
                    title=ft.Text("Phan 1", color="black", weight=ft.FontWeight.BOLD), 
                    expanded=True,
                    controls=[phan1_content]
                )
            ),
            # Sectie 2
            ft.Container(
                border=ft.Border(bottom=ft.BorderSide(1, "#D3D3D3")),
                theme=ft.Theme(divider_color="transparent"),
                content=ft.ExpansionTile(
                    title=ft.Text("Phan 2", color="black", weight=ft.FontWeight.BOLD), 
                    controls=[ft.Text("No questions", color="grey")]
                )
            ),
            # Sectie 3
            ft.Container(
                border=ft.Border(bottom=ft.BorderSide(1, "#D3D3D3")),
                theme=ft.Theme(divider_color="transparent"),
                content=ft.ExpansionTile(
                    title=ft.Text("Phan 3", color="black", weight=ft.FontWeight.BOLD), 
                    controls=[ft.Text("No questions", color="grey")]
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
                    width=340, height=45, bgcolor="#D9D9D9", border_radius=22, alignment=ft.Alignment(0, 0),
                    content=ft.Text("Save", color="black", size=16, weight=ft.FontWeight.W_500)
                )
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

    return ft.Container(width=393, height=852, bgcolor="#FFFFFF", content=ft.Column([top_bar, student_info, accordion_lists, ft.Container(expand=True), save_button_area], spacing=0))