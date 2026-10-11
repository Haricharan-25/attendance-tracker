import os
import re

from dotenv import load_dotenv
from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

from attendance.services.mongodb_service import save_attendance, save_timetable

load_dotenv()

GEMS_URL = "http://mitsims.in/#"


class GemsAttendanceError(Exception):
    pass


async def get_gems_attendance(username=None, password=None, return_timetable=False):
    """
    Login to GEMS and return the latest attendance (and optionally timetable).

    Returns:
        [
            {
                "sno": 1,
                "subject": "23CSE109",
                "attended": 12,
                "total": 18,
                "percentage": 66.67
            }
        ]
    """

    username = username or os.getenv("GEMS_USERNAME")
    password = password or os.getenv("GEMS_PASSWORD")

    if not username:
        raise GemsAttendanceError(
            "GEMS username is missing."
        )

    if not password:
        raise GemsAttendanceError(
            "GEMS password is missing."
        )

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

        page = await browser.new_page()

        try:

            # ==================================================
            # OPEN GEMS
            # ==================================================

            print("Opening GEMS...")

            await page.goto(
                GEMS_URL,
                wait_until="domcontentloaded",
                timeout=15000,
            )

            # ==================================================
            # STUDENT LOGIN
            # ==================================================

            print("Opening Student login...")

            student_option = page.locator(
                "#studentLink"
            )

            await student_option.wait_for(
                state="visible",
                timeout=8000,
            )

            await student_option.click()

            # ==================================================
            # LOGIN FORM
            # ==================================================

            student_form = page.locator(
                "#studentForm"
            )

            await student_form.wait_for(
                state="visible",
                timeout=8000,
            )

            print("Logging in...")

            await student_form.locator(
                "#inputStuId"
            ).fill(username)

            await student_form.locator(
                "#inputPassword"
            ).fill(password)

            await student_form.locator(
                "#studentSubmitButton"
            ).click()

            # ==================================================
            # WAIT FOR DASHBOARD
            # ==================================================

            print("Waiting for GEMS dashboard...")

            # Don't depend on studentIndex.html.
            # This GEMS application may load the dashboard
            # without a reliable URL change.
            await page.wait_for_timeout(5000)

            print(
                "Current URL:",
                page.url
            )

            try:

                body_text = await page.locator(
                    "body"
                ).inner_text()

            except Exception:

                body_text = ""

            if (
                "Dashboard" in body_text
                or "Progress Report" in body_text
                or "Transcript" in body_text
            ):

                print("Login successful.")

            else:

                raise GemsAttendanceError(
                    "GEMS login could not be confirmed."
                )

            # ==================================================
            # 1. SCRAPE TIMETABLE (DASHBOARD TOOLBAR)
            # ==================================================
            timetable_map = {}
            try:
                print()
                print("Looking for Time Table on dashboard toolbar...")
                tt_clicked = False
                for attempt in range(1, 7):
                    print(f"Time Table click attempt {attempt}/6...")
                    try:
                        # Priority 1: Direct button locator (#tmeTable is the GEMS button ID)
                        tt_btn = page.locator("#tmeTable button, #tmeTable")
                        if await tt_btn.count() > 0 and await tt_btn.first.is_visible():
                            await tt_btn.first.click()
                            tt_clicked = True
                            print("Clicked #tmeTable button.")
                            break

                        # Priority 2: ExtJS component click
                        clicked = await page.evaluate("""() => {
                            if (window.Ext && Ext.getCmp && Ext.getCmp('tmeTable')) {
                                const cmp = Ext.getCmp('tmeTable');
                                if (cmp.btnEl && cmp.btnEl.dom) {
                                    cmp.btnEl.dom.click();
                                    return true;
                                }
                            }
                            return false;
                        }""")
                        if clicked:
                            tt_clicked = True
                            print("Clicked tmeTable via ExtJS component.")
                            break

                        # Priority 3: Visible text link
                        text_links = page.get_by_text("Time Table", exact=True)
                        for t_idx in range(await text_links.count()):
                            el = text_links.nth(t_idx)
                            if await el.is_visible():
                                await el.click()
                                tt_clicked = True
                                print("Clicked Time Table text link.")
                                break
                        if tt_clicked:
                            break
                    except Exception as e:
                        print(f"Time Table click attempt {attempt} error: {e}")

                    await page.wait_for_timeout(1500)

                if tt_clicked:
                    print("Waiting for timetable grid rows...")
                    await page.wait_for_timeout(2500)
                    content = await page.content()
                    rows = re.findall(r'<tr\s+class="x-grid-row[^"]*">(.*?)</tr>', content, re.DOTALL)
                    print(f"Found {len(rows)} timetable rows.")

                    for row_html in rows:
                        cells = re.findall(r'<td\s+class="[^"]*x-grid-cell[^"]*">(.*?)</td>', row_html, re.DOTALL)
                        if not cells:
                            continue
                        day_match = re.search(r'<span[^>]*>(MON|TUE|WED|THU|FRI|SAT|SUN)</span>', cells[0], re.IGNORECASE)
                        if not day_match:
                            continue
                        day_name = day_match.group(1).upper()
                        day_classes = []
                        for cell_html in cells[1:]:
                            stripped = re.sub(r'<[^>]+>', '', cell_html).strip()
                            if not stripped or stripped in ['&nbsp;', '\xa0']:
                                continue
                            subj_matches = re.findall(r'<span\s+style="color:#161D3F;font-family:caption">(.*?)</span>', cell_html)
                            if subj_matches:
                                sc = subj_matches[0].strip()
                                if sc and sc not in ['&nbsp;', '\xa0']:
                                    day_classes.append(sc)
                        if day_classes:
                            timetable_map[day_name] = day_classes

                    if timetable_map:
                        save_timetable(username, timetable_map)
                        total_slots = sum(len(v) for v in timetable_map.values())
                        print(f"Timetable saved for {username}: {len(timetable_map)} days, {total_slots} slots found.")
                    else:
                        print("Notice: Timetable grid parsed 0 valid days.")
                else:
                    print("Notice: Could not locate Time Table button on dashboard.")
            except Exception as tt_err:
                print("Notice: Timetable scraping skipped or encountered non-fatal error:", tt_err)

            # ==================================================
            # 2. FIND ATTENDANCE
            # ==================================================

            print()
            print("Looking for Attendance menu...")

            attendance_clicked = False

            # ==================================================
            # DIRECT ATTENDANCE SEARCH
            # ==================================================

            for attempt in range(1, 7):

                print(
                    f"Attendance search attempt "
                    f"{attempt}/6..."
                )

                try:
                    # Priority 1: Direct button locator (#semActivity is GEMS Attendance ID)
                    att_btn = page.locator("#semActivity button, #semActivity")
                    if await att_btn.count() > 0 and await att_btn.first.is_visible():
                        await att_btn.first.click()
                        attendance_clicked = True
                        print("Clicked #semActivity button.")
                        break

                    # Priority 2: ExtJS component click
                    clicked = await page.evaluate("""() => {
                        if (window.Ext && Ext.getCmp && Ext.getCmp('semActivity')) {
                            const cmp = Ext.getCmp('semActivity');
                            if (cmp.btnEl && cmp.btnEl.dom) {
                                cmp.btnEl.dom.click();
                                return true;
                            }
                        }
                        return false;
                    }""")
                    if clicked:
                        attendance_clicked = True
                        print("Clicked semActivity via ExtJS component.")
                        break

                    # Priority 3: Visible text link
                    attendance_link = page.get_by_text(
                        "Attendance",
                        exact=True
                    )
                    count = await attendance_link.count()
                    for i in range(count):
                        element = attendance_link.nth(i)
                        if await element.is_visible():
                            await element.click()
                            attendance_clicked = True
                            print("Clicked Attendance text link.")
                            break
                    if attendance_clicked:
                        break
                except Exception as e:
                    print(f"Could not click Attendance {attempt}: {e}")

                await page.wait_for_timeout(1500)

            # ==================================================
            # PROGRESS REPORT FALLBACK
            # ==================================================

            if not attendance_clicked:

                print()
                print(
                    "Attendance not visible directly."
                )

                print(
                    "Opening Progress Report..."
                )

                progress_report = page.get_by_text(
                    "Progress Report",
                    exact=True
                )

                progress_count = (
                    await progress_report.count()
                )

                print(
                    "Progress Report elements:",
                    progress_count
                )

                progress_clicked = False

                for i in range(progress_count):

                    element = progress_report.nth(i)

                    try:

                        if await element.is_visible():

                            await element.click()

                            progress_clicked = True

                            print(
                                "Progress Report opened."
                            )

                            break

                    except Exception:
                        continue

                if progress_clicked:

                    # Give the GEMS interface time to
                    # render the Progress Report section.
                    await page.wait_for_timeout(2000)

                    # Search Attendance again.
                    for attempt in range(1, 7):

                        print(
                            f"Attendance search after "
                            f"Progress Report "
                            f"{attempt}/6..."
                        )

                        attendance_link = (
                            page.get_by_text(
                                "Attendance",
                                exact=True
                            )
                        )

                        count = (
                            await attendance_link.count()
                        )

                        print(
                            "Attendance elements:",
                            count
                        )

                        for i in range(count):

                            element = (
                                attendance_link.nth(i)
                            )

                            try:

                                if await element.is_visible():

                                    print(
                                        "Clicking Attendance..."
                                    )

                                    await element.click()

                                    attendance_clicked = True

                                    break

                            except Exception:
                                continue

                        if attendance_clicked:
                            break

                        await page.wait_for_timeout(1500)

            # ==================================================
            # ATTENDANCE NOT FOUND
            # ==================================================

            if not attendance_clicked:

                print()
                print("=" * 60)
                print("ATTENDANCE LINK NOT FOUND")
                print("=" * 60)

                print(
                    "Current URL:",
                    page.url
                )

                try:

                    body_text = await page.locator(
                        "body"
                    ).inner_text()

                    print()
                    print("PAGE TEXT:")
                    print("-" * 60)
                    print(body_text[:10000])
                    print("-" * 60)

                except Exception as e:

                    print(
                        "Could not read page:",
                        e
                    )

                # Debug screenshot
                await page.screenshot(
                    path="gems_debug.png",
                    full_page=True,
                )

                # Debug HTML
                with open(
                    "gems_debug.html",
                    "w",
                    encoding="utf-8",
                ) as file:

                    file.write(
                        await page.content()
                    )

                raise GemsAttendanceError(
                    "Attendance link not found. "
                    "gems_debug.png and "
                    "gems_debug.html were saved."
                )

            # ==================================================
            # WAIT FOR ATTENDANCE DATA
            # ==================================================

            print()
            print(
                "Waiting for attendance data..."
            )

            fields = page.locator(
                ".x-form-display-field"
            )

            await fields.first.wait_for(
                state="visible",
                timeout=10000,
            )

            count = await fields.count()

            print(
                f"Found {count} display fields."
            )

            # ==================================================
            # FIND S.NO
            # ==================================================

            start_index = None

            for i in range(count):

                try:

                    text = (
                        await fields.nth(i)
                        .inner_text()
                    ).strip()

                    if text.upper() == "S.NO":

                        start_index = i

                        print(
                            f"Attendance table found "
                            f"at field {i}."
                        )

                        break

                except Exception:
                    continue

            # ==================================================
            # TABLE NOT FOUND
            # ==================================================

            if start_index is None:

                print(
                    "Attendance table not found."
                )

                await page.screenshot(
                    path="gems_attendance_debug.png",
                    full_page=True,
                )

                raise GemsAttendanceError(
                    "Attendance table not found."
                )

            # ==================================================
            # EXTRACT ATTENDANCE
            # ==================================================

            attendance = []

            i = start_index + 5

            while i + 4 < count:

                try:

                    sno = (
                        await fields.nth(i)
                        .inner_text()
                    ).strip()

                    subject = (
                        await fields.nth(i + 1)
                        .inner_text()
                    ).strip()

                    attended = (
                        await fields.nth(i + 2)
                        .inner_text()
                    ).strip()

                    total = (
                        await fields.nth(i + 3)
                        .inner_text()
                    ).strip()

                    percentage = (
                        await fields.nth(i + 4)
                        .inner_text()
                    ).strip()

                except Exception:

                    break

                # Stop if this isn't a valid row.
                if not sno.isdigit():
                    break

                try:

                    sno_value = int(sno)
                    attended_value = int(attended)
                    total_value = int(total)

                    # Calculate percentage ourselves.
                    if total_value > 0:

                        percentage_value = round(
                            (
                                attended_value
                                / total_value
                            ) * 100,
                            2,
                        )

                    else:

                        percentage_value = 0.0

                    attendance.append(
                        {
                            "sno": sno_value,
                            "subject": subject,
                            "attended": attended_value,
                            "total": total_value,
                            "percentage": percentage_value,
                        }
                    )

                except ValueError:

                    break

                i += 5

            # ==================================================
            # NO ATTENDANCE DATA
            # ==================================================

            if not attendance:

                raise GemsAttendanceError(
                    "No attendance records found."
                )

            # ==================================================
            # SUCCESS
            # ==================================================

            print()
            print("=" * 60)
            print(
                f"Successfully extracted "
                f"{len(attendance)} subjects."
            )
            print("=" * 60)

            for item in attendance:

                print(
                    f"{item['sno']:2} | "
                    f"{item['subject']:15} | "
                    f"{item['attended']:2}/"
                    f"{item['total']:2} | "
                    f"{item['percentage']:.2f}%"
                )

            print("=" * 60)
            # ==================================================
            # SAVE ATTENDANCE TO MONGODB
            # ==================================================

            try:
                save_attendance(
                    username,
                    attendance,
                )

                print(
                    "Attendance saved to MongoDB."
                )

            except Exception as e:
                print(
                    "MongoDB save failed:",
                    e,
                )

            if return_timetable:
                return attendance, timetable_map
            return attendance

        except PlaywrightTimeoutError as e:

            raise GemsAttendanceError(
                "GEMS took too long to respond."
            ) from e

        finally:

            await browser.close()