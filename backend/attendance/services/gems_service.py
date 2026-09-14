import os

from dotenv import load_dotenv
from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

from attendance.services.mongodb_service import save_attendance

load_dotenv()

GEMS_URL = "http://mitsims.in/#"


class GemsAttendanceError(Exception):
    pass


async def get_gems_attendance(username=None, password=None):
    """
    Login to GEMS and return the latest attendance.

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
            # FIND ATTENDANCE
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

                attendance_link = page.get_by_text(
                    "Attendance",
                    exact=True
                )

                count = await attendance_link.count()

                print(
                    "Attendance elements:",
                    count
                )

                for i in range(count):

                    element = attendance_link.nth(i)

                    try:

                        if await element.is_visible():

                            print(
                                f"Clicking Attendance "
                                f"element {i}..."
                            )

                            await element.click()

                            attendance_clicked = True

                            print(
                                "Attendance clicked."
                            )

                            break

                    except Exception as e:

                        print(
                            f"Could not click Attendance "
                            f"{i}: {e}"
                        )

                if attendance_clicked:
                    break

                await page.wait_for_timeout(2000)

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

            return attendance

        except PlaywrightTimeoutError as e:

            raise GemsAttendanceError(
                "GEMS took too long to respond."
            ) from e

        finally:

            await browser.close()