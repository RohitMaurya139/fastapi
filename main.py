"""
main.py
-------
Simple FastAPI application by Rohit Maurya.

This module defines a few read-only endpoints that return JSON responses.
It also shows how to serve data loaded from a local JSON file.

Run the app with:
    python -m uvicorn main:app --reload

Then open the interactive docs at:
    http://127.0.0.1:8000/docs
"""

import json
from typing import Optional

from fastapi import FastAPI ,HTTPException, Path, Query
from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator

# Create the FastAPI application instance.
# `app` is the object uvicorn looks for (main:app).
app = FastAPI(
    title="Student API",
    description="A beginner-friendly FastAPI example serving student data.",
    version="1.0.0",
)


@app.get("/")
def greet():
    """
    Root endpoint.

    Returns a simple greeting so we can verify the server is running.

    Example response:
        {"Hello from FastAPi by rohit maurya"}
    """
    return {"Hello from FastAPi by rohit maurya"}


@app.get("/hello")
def greet_hello():
    """
    Alternate greeting endpoint.

    Same idea as `/`, but a separate path to demonstrate that each
    route maps to its own handler function.
    """
    return {"Hello from FastAPi by rohit maurya via /hello"}


def get_data():
    """
    Helper function to read and parse the local `students.json` file.

    Returns:
        list | dict: The parsed JSON content of students.json.
    """
    with open("students.json", "r") as fs:
        return json.load(fs)
#Helper Function 2.
def save_data(data):
    with open("students.json", "w") as file:
        json.dump(data, file, indent=4) #indent=4 keeps the file readable

@app.get("/get_all_student")
def student():
    """
    Return all students stored in `students.json`.

    The helper `get_data()` handles reading and decoding the file,
    and FastAPI automatically serializes the returned Python object
    to a JSON response with HTTP status 200 (OK).
    """
    return get_data()


# ---------------------------------------------------------------------------
# HTTP Status Codes
# ---------------------------------------------------------------------------
# Status codes are 3-digit numbers returned by the server to tell the client
# what happened with the request. They are grouped by their first digit:
#
#   1xx -> Informational (request received, continuing)
#   2xx -> Success
#   3xx -> Redirection
#   4xx -> Client error (the request was wrong)
#   5xx -> Server error (the server failed)
#
# Common codes used in FastAPI:
#
#   200 OK                    - Request succeeded (default for GET).
#   201 Created               - A new resource was created (default for POST).
#   204 No Content            - Success, but no body to return (e.g. DELETE).
#   400 Bad Request           - Client sent invalid or malformed data.
#   401 Unauthorized          - Authentication is required / missing or invalid.
#   403 Forbidden             - Authenticated, but not allowed to access.
#   404 Not Found             - The requested resource does not exist.
#   422 Unprocessable Entity  - Validation failed (FastAPI's default for bad input).
#   500 Internal Server Error - Something broke on the server side.
#
# How to set a custom status code in FastAPI:
#
#   from fastapi import status
#
#   @app.post("/students", status_code=status.HTTP_201_CREATED)
#   def create_student():
#       ...
#
# How to return an error with a specific code:
#
#   from fastapi import HTTPException
#
#   @app.get("/students/{student_id}")
#   def get_student(student_id: int):
#       data = get_data()
#       if student_id >= len(data):
#           raise HTTPException(
#               status_code=status.HTTP_404_NOT_FOUND,
#               detail="Student not found",
#           )
#       return data[student_id]
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# PATH PARAMETERS
# ---------------------------------------------------------------------------
# A path parameter is part of the URL itself, e.g. /student/S001.
# In FastAPI you declare it inside the route as {student_id} and then
# accept a matching function argument. FastAPI validates it and documents
# it automatically in /docs.


@app.get("/student/{student_id}")
def get_student(
    student_id: str = Path(
        ...,
        description="student ID must be Required",
        example="S001",
    )
):
    """
    Get a single student by their ID.

    Args:
        student_id (str): The ID of the student to look up (e.g. "S001").
                          Declared with `Path(...)` to mark it as required.

    Returns:
        dict: The student record matching `student_id`.

    Raises:
        HTTPException 404: If no student exists with the given ID.

    Status codes:
        200 - Student found and returned.
        404 - Student not found (we raise HTTPException with 404).
    """
    # students.json is a dict keyed by student ID, e.g. {"S001": {...}, ...}
    students = get_data()

    # Check membership in the dict keys before accessing it.
    if student_id in students:
        return students[student_id]

    # Not found -> respond with 404 and a helpful message.
    raise HTTPException(status_code=404, detail="Student not found")


# ---------------------------------------------------------------------------
# QUERY PARAMETERS
# ---------------------------------------------------------------------------
# A query parameter comes after the "?" in a URL, e.g. /filter?course=Python.
# Declaring it with `Query(...)` gives FastAPI validation, defaults, and docs.
# `Optional[str]` + default `None` makes the parameter optional.


@app.get("/filter")
def filter_student(
    course: Optional[str] = Query(
        None,
        description="Show students belonging only to this course",
        examples=["Python"],  # Correct Pydantic v2 syntax
    )
):
    """
    Filter students by course name (case-insensitive).

    Args:
        course (Optional[str]): Course to filter by, e.g. "Python".
                                If omitted (None), all students are returned.

    Returns:
        dict: A mapping of student_id -> student info for matching students,
              or the full dataset when no course is provided.

    Status codes:
        200 - Request processed successfully (even if zero matches).
    """
    student = get_data()
    res = {}

    # 1. If no course parameter is provided, return all students instead of crashing
    if course is None:
        return student

    for id, info in student.items():
        # 2. Safely call .lower() now that we know 'course' is definitely a string
        if info["course"].lower() == course.lower():
            res[id] = info

    return res


# Allowed values for the /sort endpoint, used for validation below.
SORT_FIELDS = ["marks", "age", "name"]
SORT_ORDER = ["asc", "desc"]


@app.get("/sort")
def sort_student(
    sort_by: str = Query(
        None,
        description="Sort by marks, name, age",
        examples=["marks"],
    ),
    order: str = Query(
        "asc",
        description="asc or desc",
        examples=["asc", "desc"],
    ),
):
    """
    Sort all students by a chosen field and direction.

    Args:
        sort_by (str): Field to sort on. Must be one of SORT_FIELDS
                       ("marks", "age", "name").
        order (str): Sort direction, "asc" or "desc". Defaults to "asc".

    Returns:
        list[dict]: Student records sorted by `sort_by`, each including
                    its "id".

    Raises:
        HTTPException: If `sort_by` or `order` is not an allowed value.

    Status codes:
        200 - Students returned sorted.
        404 - Invalid `sort_by` or `order` value (as written here).
              Note: 400 Bad Request is often more appropriate for invalid
              query values; 422 is FastAPI's default for validation errors.
    """
    # Validate the requested sort field against the allow-list.
    if sort_by not in SORT_FIELDS:
        raise HTTPException(
            status_code=404,
            detail=f"Invalid Sort_by '{sort_by}, Choose from {SORT_FIELDS}",
        )

    # Validate the requested sort direction against the allow-list.
    if order not in SORT_ORDER:
        raise HTTPException(
            status_code=404,
            detail=f"Invalid Sort_order '{order}, Choose from {SORT_ORDER}",
        )

    data = get_data()
    student = []

    # Convert the dict into a list so it can be sorted easily,
    # while copying each student's key into an "id" field.
    for std_id, info in data.items():
        info["id"] = std_id
        student.append(info)

    # Descending when order == "desc", otherwise ascending.
    reverse = order == "desc"
    sorted_std = sorted(student, key=lambda s: s[sort_by], reverse=reverse)
    return sorted_std


# ---------------------------------------------------------------------------
# PAGINATION
# ---------------------------------------------------------------------------
# Pagination splits a large list into smaller pages.
# Formula:
#   start = (page - 1) * limit
#   end   = start + limit
# Query params: page and limit.
# `ge` = greater than or equal, `le` = less than or equal (validation bounds).


@app.get("/pagination")
def paginate_student(
    page: int = Query(1, ge=1, description="give me page number", example=1),
    limit: int = Query(
        5, ge=1, le=20, description="record per page", example=5
    ),
):
    """
    Return one page of students.

    Args:
        page (int): Page number to fetch, starting at 1 (must be >= 1).
        limit (int): Records per page (1 to 20), default 5.

    Returns:
        dict: Pagination metadata plus the requested slice of students:
            {
                "page": current page,
                "limit": records per page,
                "total_student": total number of students,
                "student": list of students on this page
            }

    Status codes:
        200 - Page returned successfully.
        422 - If `page` or `limit` is out of the allowed range
              (FastAPI handles this automatically via `ge`/`le`).
    """
    data = get_data()

    # Compute the slice boundaries for the requested page.
    start = (page - 1) * limit
    end = start + limit

    # Flatten the dict into a list, adding each student's id.
    student = []
    for student_id, info in data.items():
        info["id"] = student_id
        student.append(info)

    # Slice out just this page's records.
    res = student[start:end]
    total_std = len(student)
    return {
        "page": page,
        "limit": limit,
        "total_student": total_std,
        "student": res,
    }

# ---------------------------------------------------------------------------
# REQUEST BODY MODELS (Pydantic)
# ---------------------------------------------------------------------------
# A Pydantic model describes the shape of the data a client sends.
# When used as a parameter type in a POST/PUT route, FastAPI reads the JSON
# body, validates it against the model and passes us a clean, typed object.
# Invalid data is rejected automatically with HTTP 422.


class Student(BaseModel):
    """
    Full student model used when CREATING a student (POST /create).

    Every field is required (Field(...) marks it as required), so the client
    must send all of them. Along with type checking, Field(...) adds rules:
        - name:   2 to 50 characters
        - age:    greater than 0 and less than-or-equal to 100
        - course: at most 50 characters
        - marks:  0 to 100 (inclusive)
        - email:  must be a valid email address (EmailStr)

    Extra behaviour:
        - check_name() normalises the name and rejects digits/symbols.
        - grade is a computed, read-only field derived from marks.
    """

    id      : str = Field(..., examples=["S001"])   # required; examples show in /docs
    name    : str = Field(..., min_length=2, max_length=50)
    age     : int = Field(..., gt=0, le=100)         # 0 < age <= 100
    course  : str = Field(..., max_length=50)
    marks   : int = Field(..., ge=0, le=100)         # 0 <= marks <= 100
    email   : EmailStr                               # built-in email validation

    # Custom validation rule for the "name" field only.
    # Runs after type/length checks pass, before the value is stored.
    @field_validator("name")  # e.g. name="Kabir singh"
    @classmethod
    def check_name(cls, value: str) -> str:
        # Remove spaces first so "Rohit Maurya" is allowed, then require
        # letters only (rejects "Rohit123" or "R0hit").
        if not value.replace(" ", "").isalpha():
            raise ValueError("Name must contain only letters and spaces")

        # Normalise the stored value: "kabir singh" -> "Kabir Singh".
        return value.title()

    @computed_field
    @property
    def grade(self) -> str:
        """
        Read-only field derived from `marks` (never sent by the client).

        @computed_field also includes "grade" in model_dump() output, so it
        shows up in API responses; the value is recalculated on each access.
        """
        if self.marks >= 90:
            return "A+"
        elif self.marks >= 80:
            return "A"
        elif self.marks >= 70:
            return "B"
        elif self.marks >= 60:
            return "C"
        else:
            return "F"

# ---------------------------------------------------------------------------
# CREATE (POST) - request body
# ---------------------------------------------------------------------------
# Because the parameter is typed as `Student`, FastAPI expects a JSON body and
# validates it against the model. status_code=201 means "Created".


@app.post('/create', status_code=201)
def create_student(student: Student):
    """
    Create a new student.

    Args:
        student (Student): Validated request body.

    Returns:
        dict: Success message plus the created student (including grade).

    Raises:
        HTTPException 400: If a student with the same id already exists.

    Status codes:
        201 - Student created successfully.
        400 - Duplicate id.
        422 - Body failed validation (FastAPI handles this automatically).
    """
    data = get_data()

    # Reject duplicates: students.json is keyed by student id.
    if student.id in data:
        raise HTTPException(status_code=400, detail=f"student ID' {student.id} already exist")

    # Store the student WITHOUT "id" (it is the dict key) and without "grade"
    # (it is derived from marks and recomputed on read).
    data[student.id] = student.model_dump(exclude={"id", "grade"})
    save_data(data)

    return {"Message": "Student created Successfully", "Student": student}

# ---------------------------------------------------------------------------
# UPDATE (PUT) - partial update model
# ---------------------------------------------------------------------------
# For updates every field is optional: the client sends only what changes.
# `Field(None, ...)` sets the default to None, which is what makes the field
# optional. (Using Field(...) here would make it required and cause a 422.)


class updateStudent(BaseModel):
    """
    Partial-update model used by PUT /update/{student_id}.

    Every field defaults to None, so omitted fields are simply "not updated".
    The endpoint uses model_dump(exclude_unset=True) to merge ONLY the fields
    the client actually sent into the existing record.
    """

    name    : str | None = Field(None, min_length=2, max_length=50)
    age     : int | None = Field(None, gt=0, le=100)
    course  : str | None = Field(None, max_length=50)
    marks   : int | None = Field(None, ge=0, le=100)
    email   : EmailStr | None


@app.put('/update/{student_id}')
def update_student(
    student_update: updateStudent,
    student_id: str = Path(
        ...,
        description="Student ID must required",
        examples=["S001"],
    ),
):
    """
    Update an existing student with only the fields that are provided.

    Args:
        student_update (updateStudent): Optional fields to change.
        student_id (str): Path parameter identifying the student.

    Returns:
        dict: Success message plus the submitted changes.

    Raises:
        HTTPException 404: If no student exists with `student_id`.

    Status codes:
        200 - Student updated successfully.
        404 - Student not found.
        422 - Body/path failed validation (FastAPI handles this automatically).

    How the partial merge works:
        1. Load the current data.
        2. exclude_unset=True keeps only the fields the client actually sent.
        3. Copy those values onto the existing record.
        4. Re-validate the merged record with the strict `Student` model so
           bad results are caught before saving.
    """
    data = get_data()

    # The student must already exist before we can update it.
    if student_id not in data:
        raise HTTPException(status_code=404, detail=f"student ID' {student_id} does not exist")

    existing = data[student_id]

    # Keep only the fields present in the request body (untouched fields are
    # left out, so they keep their old values).
    update = student_update.model_dump(exclude_unset=True)

    # Merge the submitted fields into the stored record.
    for key, value in update.items():
        existing[key] = value

    # Re-validate the final record against the full Student schema
    # (also recomputes grade). Raises if the merged data is invalid.
    student = Student(id=student_id, **existing)

    # Persist without "id" (used as the dict key) and "grade" (recomputed).
    data[student_id] = student.model_dump(exclude={"id", "grade"})
    save_data(data)

    return {"Message": "Student updated Successfully", "Updated Student": student_update}


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------
@app.delete('/delete/{student_id}')
def delete_student(
    student_id: str = Path(..., description="The Id of the student", examples=["S001"])
):
    """
    Delete a student by ID.

    Args:
        student_id (str): Path parameter identifying the student to remove.

    Returns:
        dict: A confirmation message.

    Raises:
        HTTPException 404: If no student exists with `student_id`.

    Status codes:
        200 - Student deleted successfully.
        404 - Student not found.
    """
    data = get_data()

    # Only delete a record that actually exists.
    if student_id not in data:
        raise HTTPException(
            status_code=404,
            detail=f"Student with id '{student_id}' not found"
        )

    # Remove the record and persist the updated file.
    del data[student_id]
    save_data(data)

    return {"message": f"Student '{student_id}' deleted successfully"}

    