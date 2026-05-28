# Endpoint Documentation # 


## Key Endpoints ##

### Landing - "/" ###

Parameters: ID (FK to Photo Resource)

Response: HTML page that showcases a single photo.

Template Context Variables:

user : auth.User
image : Image
current_version : ImageVersion

### Judges-St-County "judges/<str:state>/<str:county>/" ###

### Court "judges/<str:court_id>/" ###

Parameters: court_id

Response: Judicial dashboard with judge cards, infographic, tenure and radar charts.

Template Context Variables:
"court": court
"court_id": court_id
"court_formatted": court_formatted
"details": details
gantt_data": court.gantt_json().text
"radar_data": []
"state": state
"county": county
"fallback_url": fallback url to judges_state_county

### Show_Person "people/<int:person_id>/" ###

### Elections-St-County "elections/<str:state>/<str:county>/" ###

### Analysis "analysis/" ###





## Mostly Deprecated Endpoints ##
### Judges "judges/" ###
Parameters: request

Response: HTML page with state and county dropdown. Redirects upon submission,
skips if cached geodata available.

Template Context Variables:

"header": title
"preamble": blurb_about_page
"states": US_STATES
"button_name": "Find judges"
"fallback_url": reverse("judgement_call:landing")
"state": request.session.get("state")
"county": request.session.get("county")

### Elections "elections/" ###

## Viz Related Endpoints ##

## Predominantly Text Endpoints ##

### About "about/" ###

### 

## Other ##

### Get Counties "api/counties/<str:state>/" ###
Parameters: state

Response: API that returns available counties in that state to second dropdown.

Template Context Variables: N/A


    path(
        "judges/<str:state>/<str:county>/",
        views.judges_state_county,
        name="judges_state_county",
    ),
    path("people/<int:person_id>/", views.show_person, name="show_person"),
    path("methodology/", views.methodology, name="methodology"),
    path("about/", views.about, name="about"),
    path("elections/", views.elections, name="elections"),
    path(
        "elections/<str:state>/<str:county>/",
        views.elections_state_county,
        name="elections_state_county",
    ),
    path("analysis/", views.analysis, name="analysis"),
    path("analysis/polarization/", views.polarization, name="polarization"),
    path("analysis/spacejam/", views.spacejam, name="spacejam"),
    path("api/counties/<str:state>/", views.get_counties, name="get_counties"),
    path("gantt/", views.gantt, name="gantt"),
    path(
        "radar/<str:court_id>/<str2list:persons>/",
        views.get_individual_opinions_for_radar,
        name="radar",
    ),
    path("spacejam/", views.spacejam_backup, name="spacejam_backup"),
