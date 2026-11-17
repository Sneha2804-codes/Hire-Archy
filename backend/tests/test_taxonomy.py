"""Engineering taxonomy, geographic normalization, and public API tests."""

import asyncio

from app.api.taxonomy import get_taxonomy
from app.etl.cleaner import clean_jobs
from app.etl.taxonomy import ENGINEERING_TAXONOMY, REGIONS, classify_job, extract_canonical_skills


def test_full_hierarchy_and_regions_are_exposed_by_taxonomy_endpoint():
    response = asyncio.run(get_taxonomy())
    assert response == {"branches": ENGINEERING_TAXONOMY, "regions": REGIONS}
    assert len(response["branches"]) == 7
    assert response["regions"] == ["India", "APAC", "Europe", "North America", "Middle East", "Global/Remote"]


def test_engineering_branch_domain_and_geo_classification():
    india_job = classify_job(
        "VLSI Design Engineer",
        "Develop ASIC verification flows using Verilog and semiconductor design tools.",
        "Bengaluru, India",
        "",
        "onsite",
    )
    assert india_job == {
        "engineering_branch": "Electrical & Electronics",
        "domain": "VLSI & Semiconductors",
        "region": "India",
        "country": "India",
    }

    gulf_job = classify_job("Process Engineer", "Operate Aspen HYSYS at refinery projects.", "Dubai", "", "onsite")
    assert gulf_job["engineering_branch"] == "Chemical & Process"
    assert gulf_job["domain"] == "Process Engineering"
    assert gulf_job["region"] == "Middle East"
    assert gulf_job["country"] == "UAE"


def test_canonical_skills_include_software_and_core_engineering_tools():
    skills = extract_canonical_skills(
        "Python, ReactJS, AutoCAD, SolidWorks, ANSYS, MATLAB, CATIA, Revit, "
        "STAAD.Pro, PLC/SCADA, ETAP, Verilog, Embedded C, Six Sigma, "
        "Lean Manufacturing, Aspen HYSYS, Primavera P6, GD&T, FEA and CFD"
    )
    assert {"Python", "React", "AutoCAD", "SolidWorks", "ANSYS", "MATLAB", "CATIA", "Revit"}.issubset(skills)
    assert {"STAAD.Pro", "PLC/SCADA", "ETAP", "Verilog", "Embedded C", "Six Sigma"}.issubset(skills)
    assert {"Lean Manufacturing", "Aspen HYSYS", "Primavera P6", "GD&T", "FEA", "CFD"}.issubset(skills)


def test_cleaner_persists_taxonomy_and_live_flag():
    frame, _ = clean_jobs([{
        "title": "Senior Data Engineer",
        "company": "Northstar Data",
        "location": "Remote - USA",
        "description": "Build global analytics pipelines using Python and SQL.",
        "apply_url": "https://jobs.northstar.test/data-engineer",
        "country": "United States",
    }])
    row = frame.iloc[0]
    assert row["engineering_branch"] == "Computer Science & IT"
    assert row["domain"] == "Data Science & Analytics"
    assert row["region"] == "North America"
    assert row["country"] == "United States"
    assert bool(row["is_live"]) is True
