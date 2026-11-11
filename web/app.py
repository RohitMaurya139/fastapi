"""
app.py
------
Streamlit frontend for the Student API defined in ../main.py.

The UI talks to the FastAPI backend over HTTP, so the backend must be running
first (CORS is already enabled in main.py).

Run the backend (from the project root):
    python -m uvicorn main:app --reload

Run the frontend (from the project root):
    streamlit run web/app.py
"""

import html
import os
from math import ceil
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

DEFAULT_API_URL = os.getenv("STUDENT_API_URL", "http://127.0.0.1:8000")
SORT_FIELDS = ["name", "marks", "age", "course", "id"]
GRADE_ORDER = ["A+", "A", "B", "C", "F"]

st.set_page_config(
    page_title="Student Management",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
def load_css() -> None:
    """Inject the custom stylesheet that lives next to this file."""
    css_path = Path(__file__).with_name("style.css")
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------
class APIError(Exception):
    """Raised when the Student API returns an error or cannot be reached."""


def current_api_url() -> str:
    return st.session_state.get("api_url", DEFAULT_API_URL).rstrip("/")


def extract_error(response: requests.Response) -> str:
    """Turn a FastAPI error response into one readable message."""
    try:
        payload = response.json()
    except ValueError:
        return f"HTTP {response.status_code}: {response.text[:200]}"

    detail = payload.get("detail") if isinstance(payload, dict) else None
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if isinstance(item, dict):
                location = ".".join(str(p) for p in item.get("loc", []) if p != "body")
                message = item.get("msg", "invalid value")
                parts.append(f"{location}: {message}" if location else message)
            else:
                parts.append(str(item))
        return "; ".join(parts) or str(payload)
    if detail:
        return str(detail)
    return str(payload)


def api_request(method: str, path: str, base_url: str | None = None, **kwargs):
    """Send a request to the backend and return decoded JSON (or None)."""
    base = (base_url or current_api_url()).rstrip("/")
    url = f"{base}{path}"
    kwargs.setdefault("timeout", 15)

    try:
        response = requests.request(method, url, **kwargs)
    except requests.exceptions.ConnectionError as exc:
        raise APIError(f"Cannot reach the API at {base}. Is the backend running?") from exc
    except requests.exceptions.Timeout as exc:
        raise APIError("The API request timed out. Please try again.") from exc

    if not response.ok:
        raise APIError(extract_error(response))
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        return response.text


@st.cache_data(ttl=5, show_spinner=False)
def fetch_all_students(base_url: str) -> dict:
    data = api_request("GET", "/get_all_student", base_url=base_url)
    return data if isinstance(data, dict) else {}


@st.cache_data(ttl=10, show_spinner=False)
def health_check(base_url: str) -> bool:
    try:
        api_request("GET", "/", base_url=base_url)
        return True
    except APIError:
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def grade_for(marks: int) -> str:
    if marks >= 90:
        return "A+"
    if marks >= 80:
        return "A"
    if marks >= 70:
        return "B"
    if marks >= 60:
        return "C"
    return "F"


def badge_class(grade: str) -> str:
    if grade in ("A+", "A"):
        return "badge-a"
    if grade == "B":
        return "badge-b"
    if grade == "C":
        return "badge-c"
    return "badge-f"


def to_records(data: dict) -> list[dict]:
    records = []
    for student_id, info in data.items():
        row = {"id": student_id, **info}
        row["grade"] = grade_for(int(row.get("marks", 0)))
        records.append(row)
    return records


def flash(kind: str, message: str) -> None:
    st.session_state["_flash"] = (kind, message)


def show_flash() -> None:
    item = st.session_state.pop("_flash", None)
    if not item:
        return
    kind, message = item
    (st.success if kind == "success" else st.error)(message)


def full_width() -> dict:
    """Stretch a widget to the full width of its container."""
    return {"width": "stretch"}


def page_header(title: str, subtitle: str, tag: str) -> None:
    st.markdown(
        f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p>'
        f'<span class="pill">{tag}</span></div>',
        unsafe_allow_html=True,
    )


def metric_card(label: str, value, sub: str) -> str:
    return (
        '<div class="metric-card">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-sub">{sub}</div>'
        "</div>"
    )


def student_card_html(student_id: str, info: dict) -> str:
    marks = info.get("marks", "-")
    grade = grade_for(int(marks)) if isinstance(marks, (int, float)) else "-"
    return (
        '<div class="student-card"><div class="row"><div>'
        f'<h4>{html.escape(str(info.get("name", "")))} '
        f'<span class="id-chip">{html.escape(str(student_id))}</span></h4>'
        f'<div class="meta">{html.escape(str(info.get("course", "")))}'
        f' &middot; Age {html.escape(str(info.get("age", "-")))}'
        f' &middot; {html.escape(str(info.get("email", "")))}</div>'
        "</div><div style=\"text-align:right\">"
        f'<div class="marks">{html.escape(str(marks))}</div>'
        f'<span class="badge {badge_class(grade)}">Grade {grade}</span>'
        "</div></div></div>"
    )


def empty_state(title: str, message: str) -> None:
    st.markdown(
        f'<div class="empty-state"><strong>{title}</strong>{message}</div>',
        unsafe_allow_html=True,
    )


def connection_error(error: Exception) -> None:
    st.error(str(error))
    st.info("Start the backend from the project root with: python -m uvicorn main:app --reload")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-brand">'
            '<div class="logo">S</div>'
            "<h3>Student Manager</h3>"
            "<p>FastAPI + Streamlit</p>"
            "</div>",
            unsafe_allow_html=True,
        )

        if "api_url" not in st.session_state:
            st.session_state["api_url"] = DEFAULT_API_URL
        st.text_input("API base URL", key="api_url")

        if health_check(current_api_url()):
            st.success("API connected")
        else:
            st.error("API offline")

        st.divider()
        page = st.radio(
            "Navigation",
            ["Dashboard", "Students", "Add Student", "Update Student", "Delete Student"],
            label_visibility="collapsed",
        )
        st.divider()

        if st.button("Refresh data", **full_width()):
            fetch_all_students.clear()
            st.rerun()

        st.markdown(f"[Open API docs]({current_api_url()}/docs)")
        st.caption("Tip: start uvicorn on port 8000 before using the app.")

    return page


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
def render_dashboard() -> None:
    page_header(
        "Student Dashboard",
        "A live overview of every student stored in the FastAPI backend.",
        "Analytics",
    )

    try:
        data = fetch_all_students(current_api_url())
    except APIError as exc:
        connection_error(exc)
        return

    records = to_records(data)
    if not records:
        empty_state("No students yet", "Add your first student from the Add Student page.")
        return

    df = pd.DataFrame(records)
    total = len(df)
    average = round(float(df["marks"].mean()), 1)
    courses = int(df["course"].nunique())
    pass_rate = round(float((df["marks"] >= 40).mean() * 100), 1)

    st.markdown(
        '<div class="metric-grid">'
        + metric_card("Total students", total, "Enrolled records")
        + metric_card("Average marks", average, "Across all courses")
        + metric_card("Courses", courses, "Distinct programs")
        + metric_card("Pass rate", f"{pass_rate}%", "Marks of 40 or above")
        + "</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)
    with left:
        st.markdown('<div class="section-title">Students per course</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-desc">Distribution of enrollment by program.</div>',
            unsafe_allow_html=True,
        )
        st.bar_chart(df["course"].value_counts(), height=300)

    with right:
        st.markdown('<div class="section-title">Grade distribution</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-desc">Grades are derived from marks on the backend.</div>',
            unsafe_allow_html=True,
        )
        grade_counts = df["grade"].value_counts().reindex(GRADE_ORDER).dropna()
        st.bar_chart(grade_counts, height=300)

    st.markdown('<div class="section-title" style="margin-top:18px;">Top performers</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-desc">The five highest scoring students.</div>',
        unsafe_allow_html=True,
    )
    top = sorted(records, key=lambda r: r["marks"], reverse=True)[:5]
    st.markdown("".join(student_card_html(r["id"], r) for r in top), unsafe_allow_html=True)


def render_students() -> None:
    page_header(
        "Browse Students",
        "Search, filter, sort and page through the full student directory.",
        "Directory",
    )

    try:
        records = to_records(fetch_all_students(current_api_url()))
    except APIError as exc:
        connection_error(exc)
        return

    if not records:
        empty_state("No students found", "The backend returned an empty dataset.")
        return

    with st.expander("Look up a single student by ID"):
        lookup_col, button_col = st.columns([3, 1])
        lookup_id = lookup_col.text_input("Student ID", key="lookup_id", placeholder="S002")
        if button_col.button("Find student", **full_width()):
            try:
                info = api_request("GET", f"/student/{lookup_id.strip()}")
            except APIError as exc:
                st.error(str(exc))
            else:
                st.markdown(student_card_html(lookup_id.strip(), info), unsafe_allow_html=True)

    st.divider()

    search_col, course_col, sort_col, order_col = st.columns([2.2, 1.4, 1.2, 0.8])
    search = search_col.text_input("Search", placeholder="Name, email or ID")
    courses = ["All courses"] + sorted({str(r["course"]) for r in records})
    selected_course = course_col.selectbox("Course", courses)
    sort_by = sort_col.selectbox("Sort by", SORT_FIELDS)
    order = order_col.selectbox("Order", ["asc", "desc"])

    query = search.strip().lower()
    view = [
        row
        for row in records
        if (
            not query
            or query in str(row["id"]).lower()
            or query in str(row["name"]).lower()
            or query in str(row["email"]).lower()
        )
        and (selected_course == "All courses" or str(row["course"]) == selected_course)
    ]
    view.sort(key=lambda row: row[sort_by], reverse=order == "desc")

    if not view:
        empty_state("No matching students", "Try a different search or clear the course filter.")
        return

    page_col, size_col, _ = st.columns([1, 1, 2])
    page_size = size_col.selectbox("Rows per page", [5, 10, 20], index=1)
    total_pages = max(1, ceil(len(view) / page_size))
    page = page_col.selectbox("Page", list(range(1, total_pages + 1)))

    start = (page - 1) * page_size
    end = start + page_size
    page_rows = view[start:end]

    st.caption(f"Showing {start + 1}-{min(end, len(view))} of {len(view)} students")

    table = pd.DataFrame(page_rows)[["id", "name", "age", "course", "marks", "grade", "email"]]
    st.dataframe(
        table,
        hide_index=True,
        **full_width(),
        column_config={
            "id": st.column_config.TextColumn("ID", width="small"),
            "name": st.column_config.TextColumn("Name"),
            "age": st.column_config.NumberColumn("Age", width="small"),
            "course": st.column_config.TextColumn("Course"),
            "marks": st.column_config.ProgressColumn("Marks", min_value=0, max_value=100, format="%d"),
            "grade": st.column_config.TextColumn("Grade", width="small"),
            "email": st.column_config.TextColumn("Email"),
        },
    )


def render_add_student() -> None:
    page_header(
        "Add Student",
        "Create a new record. The backend validates every field before saving.",
        "Create",
    )

    version = st.session_state.get("create_version", 0)
    with st.form(f"create_form_{version}", clear_on_submit=False):
        col_a, col_b = st.columns(2)
        student_id = col_a.text_input("Student ID", placeholder="S020")
        name = col_b.text_input("Full name", placeholder="Rohit Maurya")
        age = col_a.number_input("Age", min_value=1, max_value=100, value=20, step=1)
        marks = col_b.number_input("Marks", min_value=0, max_value=100, value=75, step=1)
        course = col_a.text_input("Course", placeholder="Python")
        email = col_b.text_input("Email", placeholder="student@example.com")
        submitted = st.form_submit_button("Create student", type="primary", **full_width())

    if not submitted:
        return

    payload = {
        "id": student_id.strip(),
        "name": name.strip(),
        "age": int(age),
        "course": course.strip(),
        "marks": int(marks),
        "email": email.strip(),
    }
    missing = [field for field in ("id", "name", "course", "email") if not payload[field]]
    if missing:
        st.error(f"Please fill in: {', '.join(missing)}")
        return

    try:
        api_request("POST", "/create", json=payload)
    except APIError as exc:
        st.error(str(exc))
        return

    fetch_all_students.clear()
    flash("success", f"Student '{payload['id']}' created successfully.")
    st.session_state["create_version"] = version + 1
    st.rerun()


def render_update_student() -> None:
    page_header(
        "Update Student",
        "Load an existing record, change what you need and save the changes.",
        "Edit",
    )

    lookup_col, button_col = st.columns([3, 1])
    lookup = lookup_col.text_input("Student ID to update", key="update_lookup", placeholder="S002")
    if button_col.button("Load student", **full_width()):
        student_id = lookup.strip()
        if not student_id:
            st.error("Enter a student ID first.")
        else:
            try:
                info = api_request("GET", f"/student/{student_id}")
            except APIError as exc:
                st.error(str(exc))
            else:
                info["id"] = student_id
                st.session_state["update_loaded"] = info

    loaded = st.session_state.get("update_loaded")
    if not loaded:
        empty_state("Nothing loaded", "Enter an ID above and click Load student.")
        return

    st.markdown(student_card_html(loaded["id"], loaded), unsafe_allow_html=True)

    token = loaded["id"]
    with st.form(f"update_form_{token}"):
        col_a, col_b = st.columns(2)
        name = col_a.text_input("Full name", value=str(loaded.get("name", "")), key=f"upd_name_{token}")
        age = col_b.number_input(
            "Age",
            min_value=1,
            max_value=100,
            value=int(loaded.get("age", 20)),
            step=1,
            key=f"upd_age_{token}",
        )
        marks = col_b.number_input(
            "Marks",
            min_value=0,
            max_value=100,
            value=int(loaded.get("marks", 0)),
            step=1,
            key=f"upd_marks_{token}",
        )
        course = col_a.text_input("Course", value=str(loaded.get("course", "")), key=f"upd_course_{token}")
        email = col_b.text_input("Email", value=str(loaded.get("email", "")), key=f"upd_email_{token}")
        submitted = st.form_submit_button("Save changes", type="primary", **full_width())

    if not submitted:
        return

    payload = {
        "name": name.strip(),
        "age": int(age),
        "course": course.strip(),
        "marks": int(marks),
        "email": email.strip(),
    }
    missing = [field for field in ("name", "course", "email") if not payload[field]]
    if missing:
        st.error(f"Please fill in: {', '.join(missing)}")
        return

    try:
        api_request("PUT", f"/update/{token}", json=payload)
    except APIError as exc:
        st.error(str(exc))
        return

    fetch_all_students.clear()
    st.session_state["update_loaded"] = {**loaded, **payload}
    flash("success", f"Student '{token}' updated successfully.")
    st.rerun()


def render_delete_student() -> None:
    page_header(
        "Delete Student",
        "Remove a record permanently. This action cannot be undone.",
        "Delete",
    )

    try:
        data = fetch_all_students(current_api_url())
    except APIError as exc:
        connection_error(exc)
        return

    version = st.session_state.get("delete_version", 0)
    student_id = st.text_input(
        "Student ID to delete", key=f"delete_id_{version}", placeholder="S002"
    )
    student_id = student_id.strip()

    if student_id:
        if student_id in data:
            st.markdown(student_card_html(student_id, data[student_id]), unsafe_allow_html=True)
        else:
            empty_state("Student not found", f"No record exists for ID '{html.escape(student_id)}'.")

    confirm = st.checkbox("I understand this will permanently delete the student.")
    if st.button("Delete student", type="primary", disabled=not (student_id and confirm), **full_width()):
        try:
            api_request("DELETE", f"/delete/{student_id}")
        except APIError as exc:
            st.error(str(exc))
        else:
            fetch_all_students.clear()
            flash("success", f"Student '{student_id}' deleted successfully.")
            st.session_state["delete_version"] = version + 1
            st.rerun()


def render_footer() -> None:
    st.markdown(
        '<div class="footer">Student Management UI &middot; Streamlit frontend for the FastAPI Student API</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    load_css()
    page = render_sidebar()
    show_flash()

    if page == "Dashboard":
        render_dashboard()
    elif page == "Students":
        render_students()
    elif page == "Add Student":
        render_add_student()
    elif page == "Update Student":
        render_update_student()
    else:
        render_delete_student()

    render_footer()


if __name__ == "__main__":
    main()
