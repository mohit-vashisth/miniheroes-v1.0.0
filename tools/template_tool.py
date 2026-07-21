from __future__ import annotations

import json
import subprocess
from pathlib import Path

import cv2
import numpy as np


# ==========================================================
# CONFIG
# ==========================================================

ADB = r"D:\LDPlayer\LDPlayer9\adb.exe"

ROOT = Path(__file__).resolve().parent.parent

TEMPLATE_DIR = ROOT / "templates"
CROP_DIR = TEMPLATE_DIR / "crops"
JSON_FILE = TEMPLATE_DIR / "templates.json"

TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
CROP_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================================
# TOOL
# ==========================================================

class TemplateTool:

    def __init__(self):

        self.serial = ""
        self.image = None
        self.display_image = None        # resized image for showing
        self._display_scale = (1.0, 1.0) # (scale_x, scale_y) from original to display
        self.click = (0, 0)

    # ------------------------------------------------------

    def run(self):

        self.detect_device()

        self.capture()

        self.pick_point()

        self.crop()

    # ------------------------------------------------------

    def detect_device(self):

        result = subprocess.run(
            [ADB, "devices"],
            capture_output=True,
            text=True,
        )

        devices = []

        for line in result.stdout.splitlines():

            if "\tdevice" in line:

                devices.append(
                    line.split()[0]
                )

        if not devices:

            raise RuntimeError(
                "No emulator found."
            )

        self.serial = devices[0]

        print(f"\nDevice : {self.serial}")

    # ------------------------------------------------------

    def capture(self):

        print("Capturing screenshot...")

        result = subprocess.run(
            [
                ADB,
                "-s",
                self.serial,
                "exec-out",
                "screencap",
                "-p",
            ],
            capture_output=True,
        )

        img = np.frombuffer(
            result.stdout,
            np.uint8,
        )

        self.image = cv2.imdecode(
            img,
            cv2.IMREAD_UNCHANGED,
        )

        if self.image is None:

            raise RuntimeError(
                "Screenshot failed."
            )

        cv2.imwrite(
            "current_screen.png",
            self.image,
        )

        if self.image.shape[2] == 4:

            self.image = cv2.cvtColor(
                self.image,
                cv2.COLOR_BGRA2BGR,
            )

    # ------------------------------------------------------

    def _resize_for_display(self, img: np.ndarray, max_width: int = 800, max_height: int = 600) -> np.ndarray:
        """Scale image to fit within max_width x max_height, keep aspect ratio."""
        h, w = img.shape[:2]
        scale = min(max_width / w, max_height / h, 1.0)   # don't upscale if image is already smaller
        if scale < 1.0:
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized = cv2.resize(img, (new_w, new_h))
            self._display_scale = (w / new_w, h / new_h)   # store scale factors to convert mouse coordinates
            return resized
        else:
            self._display_scale = (1.0, 1.0)
            return img

    # ------------------------------------------------------

    def pick_point(self):

        # Resize original image for display
        self.display_image = self._resize_for_display(self.image, max_width=800, max_height=600)

        cv2.namedWindow("Screenshot", cv2.WINDOW_NORMAL)
        cv2.imshow("Screenshot", self.display_image)

        def mouse_callback(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                # Convert display coordinates to original coordinates
                scale_x, scale_y = self._display_scale
                orig_x = int(x * scale_x)
                orig_y = int(y * scale_y)
                self.click = (orig_x, orig_y)

                # Draw on display image
                temp = self.display_image.copy()
                cv2.circle(temp, (x, y), 5, (0, 0, 255), -1)
                cv2.putText(temp, f"{orig_x},{orig_y}", (x + 10, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                cv2.imshow("Screenshot", temp)
                print(f"\nOriginal X = {orig_x}, Y = {orig_y}")

        cv2.setMouseCallback("Screenshot", mouse_callback)

        print("\nClick on the image to set the reference point.")
        print("Press C to crop, ESC to exit.")

        while True:
            key = cv2.waitKey(20) & 0xFF
            if key == ord("c"):
                break
            if key == 27:
                cv2.destroyAllWindows()
                exit()

        cv2.destroyWindow("Screenshot")

    # ------------------------------------------------------

    def crop(self):

        # Use the same display image (already resized)
        if self.display_image is None:
            self.display_image = self._resize_for_display(self.image, max_width=800, max_height=600)

        roi_display = cv2.selectROI("Crop (draw rectangle and press Enter)", self.display_image,
                                    showCrosshair=True, fromCenter=False)
        cv2.destroyWindow("Crop (draw rectangle and press Enter)")

        dx, dy, dw, dh = roi_display
        if dw == 0 or dh == 0:
            print("Cancelled.")
            return

        # Convert display ROI to original coordinates
        scale_x, scale_y = self._display_scale
        ox = int(dx * scale_x)
        oy = int(dy * scale_y)
        ow = int(dw * scale_x)
        oh = int(dh * scale_y)

        # Crop from original image
        crop_img = self.image[oy:oy + oh, ox:ox + ow]

        index = 1
        while True:
            filename = f"crop_{index:03d}.png"
            path = CROP_DIR / filename
            if not path.exists():
                break
            index += 1

        cv2.imwrite(str(path), crop_img)
        print(f"\nSaved : {filename} (original ROI: {ox},{oy},{ow},{oh})")

        self.save_json(filename)

    # ------------------------------------------------------

    def save_json(
        self,
        filename: str,
    ):

        if JSON_FILE.exists():

            with open(
                JSON_FILE,
                "r",
                encoding="utf-8",
            ) as f:

                data = json.load(f)

        else:

            data = []

        data.append(
            {
                "name": "",
                "image": filename,
                "position": {
                    "x": self.click[0],
                    "y": self.click[1],
                },
                "seconds": 1
            }
        )

        with open(
            JSON_FILE,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
            )

        print("templates.json updated.")

        print("\nDone.")


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    tool = TemplateTool()

    tool.run()