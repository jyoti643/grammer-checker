import requests
from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from markupsafe import Markup

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///essays.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Essay(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_text = db.Column(db.Text, nullable=False)
    corrected_text = db.Column(db.Text, nullable=False)

@app.route("/", methods=["GET", "POST"])
def home():
    highlighted_essay = ""
    raw_essay = ""
    corrected_essay = ""
    issues = []

    if request.method == "POST":
        raw_essay = request.form["essay"]

        # Call LanguageTool API
        response = requests.post(
            "https://api.languagetool.org/v2/check",
            data={
                'text': raw_essay,
                'language': 'en-US',
            }
        )
        result = response.json()
        matches = sorted(result.get("matches", []), key=lambda x: x["offset"])

        essay_html = raw_essay
        offset_shift = 0
        corrected_chars = list(raw_essay)

        for match in matches:
            offset = match["offset"]
            length = match["length"]
            mistake = raw_essay[offset:offset + length]
            suggestion = match["replacements"][0]["value"] if match["replacements"] else mistake
            message = match["message"]

            html_offset = offset + offset_shift
            highlight_html = f'<span class="highlight" title="{message}. Suggestion: {suggestion}">{mistake}</span>'
            essay_html = essay_html[:html_offset] + highlight_html + essay_html[html_offset + length:]
            offset_shift += len(highlight_html) - length

            issues.append({
                "mistake": mistake,
                "suggestion": suggestion,
                "message": message
            })

            corrected_chars[offset:offset + length] = list(suggestion.ljust(length))

        highlighted_essay = Markup(essay_html)
        corrected_essay = ''.join(corrected_chars).strip()

        # Save to DB
        new_essay = Essay(original_text=raw_essay, corrected_text=corrected_essay)
        db.session.add(new_essay)
        db.session.commit()

        return redirect(url_for('home'))

    # Show last 5 essays
    all_essays = Essay.query.order_by(Essay.id.desc()).limit(5).all()

    return render_template("index.html",
                           highlighted=highlighted_essay,
                           corrected=corrected_essay,
                           issues=issues,
                           essays=all_essays)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
