# frontend/edit_result_page.py
import streamlit as st
import os

def show_edit_result_page(logo_html):
    # --- 1. TOP BAR & BACK NAVIGATION ---
    params = st.query_params
    if "action" in params and params["action"] == "go_back_to_results":
        st.query_params.clear()
        st.session_state.screen = "results"
        st.rerun()

    st.markdown(f"""
    <div class="logo-container-preview">
        <a href="?action=go_back_to_results" target="_self" class="topbar-arrow-clickable">‹</a>
        <div class="topbar-title-centered">Edit Grading Results</div>
        <div class="topbar-logo-right">{logo_html}</div>
    </div>
    """, unsafe_allow_html=True)

    # Start hoofdcontent container
    st.markdown('<div class="main-content">', unsafe_allow_html=True)

    # --- 2. BUBBLE GRID STATE INITIALISATIE ---
    # We slaan de antwoorden op in st.session_state zodat aanpassingen bewaard blijven
    if "bubble_questions" not in st.session_state:
        st.session_state.bubble_questions = [
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

    # Bereken de live score op basis van het aantal groene bubbles
    correct_count = sum(
        1 for q in st.session_state.bubble_questions 
        for letter in ["A", "B", "C", "D"] if q["answers"][letter] == "green"
    )

    # --- 3. STUDENT INFO PANEL ---
    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 15px; margin-bottom: 15px; background-color: white; border-radius: 10px; border: 1px solid #E2E8F0;">
            <span style="font-size: 18px; font-weight: 500; color: #172B4D;">👤 Student Name</span>
            <span style="font-size: 18px; font-weight: bold; color: #172B4D;">🎯 Score: {correct_count} / 15</span>
        </div>
    """, unsafe_allow_html=True)

    # --- 4. ACCORDION / EXPANDERS (Phan 1, 2, 3) ---
    with st.expander("📊 Phan 1", expanded=True):
        st.write("")
        
        # Wijzigings-logica wanneer er op een bubble gedrukt wordt
        def handle_bubble_click(q_id, letter):
            for q in st.session_state.bubble_questions:
                if q["id"] == q_id:
                    current_status = q["answers"][letter]
                    # State machine: Leeg -> Groen (Correct) -> Rood (Fail) -> Leeg
                    if current_status is None:
                        new_status = "green"
                    elif current_status == "green":
                        new_status = "red"
                    else:
                        new_status = None
                    
                    # Reset de hele rij (er kan maar 1 antwoord gekozen zijn)
                    for l in ["A", "B", "C", "D"]:
                        q["answers"][l] = None
                    
                    q["answers"][letter] = new_status
                    break

        # Bouw de interactieve rijen met Streamlit knoppen
        for q in st.session_state.bubble_questions:
            col_label, col_A, col_B, col_C, col_D = st.columns([1, 1, 1, 1, 1])
            
            with col_label:
                st.markdown(f"<p style='margin-top: 8px; font-weight: bold; color: #172B4D;'>{q['id']}:</p>", unsafe_allow_html=True)
            
            # Render de letters als gekleurde buttons
            for letter, col in zip(["A", "B", "C", "D"], [col_A, col_B, col_C, col_D]):
                with col:
                    status = q["answers"][letter]
                    
                    # Bepaal dynamisch de styling per knop-type via unieke keys
                    if status == "green":
                        btn_label = f"🟢 {letter}"
                    elif status == "red":
                        btn_label = f"🔴 {letter}"
                    else:
                        btn_label = f"⚪ {letter}"
                        
                    # Zodra de leraar klikt, vuurt de callback af en herlaadt het scherm direct met de juiste score
                    st.button(
                        btn_label, 
                        key=f"bubble_{q['id']}_{letter}", 
                        on_click=handle_bubble_click, 
                        args=(q["id"], letter),
                        use_container_width=True
                    )

    with st.expander("📝 Phan 2", expanded=False):
        st.caption("No questions detected in this section.")

    with st.expander("📝 Phan 3", expanded=False):
        st.caption("No questions detected in this section.")

    # --- 5. SAVE BUTTON AREA ---
    st.write("")
    if st.button("💾 Save Changes", key="save_changes_btn", use_container_width=True):
        st.success("Changes successfully synchronized with database!")
        st.session_state.screen = "results"
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)