from app.crawlers.hockey import parse_hockey_html


def test_parse_hockey_html_single_row_minimal():
    html = """
    <html>
      <body>
        <table class="table">
          <thead>
            <tr>
              <th>Team Name</th><th>Year</th><th>Wins</th><th>Losses</th><th>OT Losses</th>
              <th>Win %</th><th>Goals For</th><th>Goals Against</th><th>+ / -</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Boston Bruins</td><td>1990</td><td>44</td><td>24</td><td>0</td>
              <td>0.55</td><td>299</td><td>264</td><td>35</td>
            </tr>
          </tbody>
        </table>
      </body>
    </html>
    """
    rows = parse_hockey_html(html)
    assert len(rows) == 1
    assert rows[0]["team_name"] == "Boston Bruins"
    assert rows[0]["year"] == 1990
    assert rows[0]["wins"] == 44
    assert rows[0]["goal_diff"] == 35


def test_parse_hockey_selects_correct_table_when_multiple_exist():
    html = """
    <html>
      <body>
        <table class="table"><tr><th>Not hockey</th></tr><tr><td>fake</td></tr></table>

        <table class="table">
          <thead>
            <tr>
              <th>Team Name</th><th>Year</th><th>Wins</th><th>Losses</th><th>OT Losses</th>
              <th>Win %</th><th>Goals For</th><th>Goals Against</th><th>+ / -</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Calgary Flames</td><td>1990</td><td>46</td><td>26</td><td>0</td>
              <td>0.575</td><td>344</td><td>263</td><td>81</td>
            </tr>
          </tbody>
        </table>
      </body>
    </html>
    """
    rows = parse_hockey_html(html)
    assert len(rows) == 1
    assert rows[0]["team_name"] == "Calgary Flames"
    assert rows[0]["goal_diff"] == 81