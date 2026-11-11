"""
PYDANTIC FUNDAMENTALS
=====================

WHY WE USE PYDANTIC? WHAT PROBLEM DOES IT SOLVE?

When data comes into our program from OUTSIDE (JSON files, API request bodies,
form inputs, databases), we cannot trust it. It may have:
    - missing keys
    - wrong types (e.g. age sent as "23" string instead of int)
    - invalid values (negative age, malformed email, empty name...)

Without Pydantic we would write endless manual checks:
    if "name" in data and isinstance(...) and len(...) ...  # repetitive!

Pydantic solves this with MODELS:
    1. Declare how the data SHOULD look (types + rules) in one place.
    2. On instantiation it automatically VALIDATES (bad data -> clear error)
       and COERCES/PARSES (e.g. the string "23" becomes int 23).
    3. Gives IDE auto-completion and type-safety for the attributes.

It is the backbone of FastAPI: request bodies are parsed with Pydantic models.
"""

from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator
import json


# ----------------------------------------------------------------------------
# STEP 1: Basic model - just type annotations, nothing else.
# Pydantic converts ("coerces") the string "23" into int 23 automatically.
# ----------------------------------------------------------------------------
# class simpleStudent(BaseModel):
#     name: str          # required, must be a string
#     age: int           # required, "23" (str) is auto-converted to 23
#     marks: int         # required

# s = simpleStudent(name="Rohit", age="23", marks=80)
# print(s.name, s.age, s.marks)          # Rohit 23 80


# ----------------------------------------------------------------------------
# STEP 2: Adding RULES with Field(...) -> validation constraints.
#   ...            = the field is REQUIRED (no default value)
#   min_length/    = string length limits
#   gt / lt / le   = numeric bounds (greater-than / less-than / less-or-equal)
#   "Python"       = default value (field becomes OPTIONAL)
#   str | None=None= optional field, defaults to None
# ----------------------------------------------------------------------------
# class ruleStudent(BaseModel):
#     name: str = Field(..., min_length=2, max_length=50)
#     age: int = Field(..., gt=0, lt=100)        # 0 < age < 100
#     marks: int = Field(..., gt=0, lt=100)      # 0 < marks < 100
#     course: str = "Python"                     # optional (has a default)
#     phone: str | None = None                   # optional, defaults to None

# s = ruleStudent(name="Rohit", age="23", marks=80)
# print(s.name, s.age, s.marks, s.course, s.phone)


# ----------------------------------------------------------------------------
# STEP 3: Special types - EmailStr validates email format
# (needs: pip install "pydantic[email]")
# ----------------------------------------------------------------------------
# class emailStudent(BaseModel):
#     name: str = Field(..., min_length=2, max_length=50)
#     email: EmailStr      # rejects "rohit123" but accepts "rohit123@gmail.com"

# s = emailStudent(name="Rohit", email="rohit123@gmail.com")
# print(s.name, s.email)


# ----------------------------------------------------------------------------
# STEP 4: Full model - Field constraints + custom validator + computed field
# ----------------------------------------------------------------------------

class Student(BaseModel):
    """
    Student model combining everything learned above:

    - Field(...)      -> required fields with rules
    - defaults        -> optional fields (course, phone)
    - EmailStr        -> built-in special type validation
    - field_validator -> CUSTOM validation logic (check_name)
    - computed_field  -> a derived value (grade) calculated from marks,
                         included in model_dump() output
    """

    # `...` means REQUIRED. `examples` is documentation only (shown in
    # FastAPI's auto-generated Swagger docs); it does NOT validate anything.
    id: str = Field(..., examples=["S001"])
    # name must be 2-50 characters long
    name: str = Field(..., min_length=2, max_length=50)
    # age must satisfy 0 < age < 100
    age: int = Field(..., gt=0, lt=100)
    # marks must satisfy 0 < marks <= 100 (le=100 allows exactly 100)
    marks: int = Field(..., gt=0, le=100)
    # optional field with a default -> never fails validation if omitted
    course: str = "Python"
    # optional field, None (null) is allowed -> JSON without "phone" is fine
    phone: str | None = None
    # required, must be a valid email address format
    email: EmailStr

    @field_validator("name")
    @classmethod
    def check_name(cls, value: str) -> str:
        """
        Custom validator that runs ONLY for the "name" field.

        1. Rejects names containing digits/symbols
           ("Rohit123" -> raises ValidationError with our message).
        2. Normalizes the value before saving:
           "rohit maurya" -> "Rohit Maurya" (title case).

        The value we RETURN is what gets stored on the model.
        """
        if not value.replace(" ", "").isalpha():  # strip spaces, then check a-z only
            raise ValueError("Name must contain only letters and spaces")
        return value.title()  # transform the data: capitalize each word

    @computed_field
    @property
    def grade(self) -> str:
        """
        Computed field: a read-only property DERIVED from existing data.

        - Not passed in by the user, not stored in input JSON.
        - Calculated every time it is accessed (s.grade).
        - @computed_field makes it appear in model_dump() /
          model_dump_json() output too (unlike a plain @property).
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


# Creating one instance manually - note the coercion: age="23" (str) -> 23 (int)
# s = Student(id="S001", name="rohit maurya", age="23", marks=99, email="rohit123@gmail.com")
# print(s.name, s.email, s.age, s.marks, s.course, s.phone, s.grade)


# model_dump() - convert the validated model BACK to a plain Python dict
# data = s.model_dump()
# print(data)          # {'id': 'S001', 'name': 'Rohit Maurya', ..., 'grade': 'A+'}
# print(type(data))    # <class 'dict'>


# ----------------------------------------------------------------------------
# REAL-WORLD USAGE: validate data loaded from a JSON file
# students.json -> Python dict -> validated Student objects, one per record
# ----------------------------------------------------------------------------
with open("students.json", "r") as file:
    raw = json.load(file)  # dict like {"S001": {...}, "S002": {...}}

for std_id, info in raw.items():
    # **info unpacks the inner dict as keyword arguments:
    # Student(id="S001", name="Aarav Sharma", age=25, ...)
    # If any record has bad data (missing email, marks=150...),
    # Pydantic raises a ValidationError pointing at the exact field.
    s = Student(id=std_id, **info)
    print(s.name, s.email, s.age, s.marks, s.course, s.phone, s.grade)
