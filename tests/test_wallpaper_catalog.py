import json
import os
import tempfile
import unittest
from unittest import mock

import panel


class WallpaperCatalogTests(unittest.TestCase):
    def test_lists_scene_and_video_projects(self):
        with tempfile.TemporaryDirectory() as root:
            scene_dir = os.path.join(root, "100")
            video_dir = os.path.join(root, "200")
            os.makedirs(scene_dir)
            os.makedirs(video_dir)

            with open(os.path.join(scene_dir, "project.json"), "w", encoding="utf-8") as stream:
                json.dump(
                    {"title": "Scene Sample", "type": "scene", "preview": "cover.jpg"},
                    stream,
                )
            open(os.path.join(scene_dir, "cover.jpg"), "wb").close()

            with open(os.path.join(video_dir, "project.json"), "w", encoding="utf-8") as stream:
                json.dump({"title": "Video Sample", "type": "video"}, stream)
            open(os.path.join(video_dir, "clip.mp4"), "wb").close()

            with mock.patch.object(panel, "find_we_workshop_dirs", return_value=[root]):
                items = panel.list_we_wallpapers()

        self.assertEqual([item["type"] for item in items], ["scene", "video"])
        self.assertTrue(items[0]["project"].endswith(os.path.join("100", "project.json")))
        self.assertTrue(items[0]["preview"].endswith(os.path.join("100", "cover.jpg")))
        self.assertIsNone(items[0]["video"])
        self.assertTrue(items[1]["video"].endswith(os.path.join("200", "clip.mp4")))


if __name__ == "__main__":
    unittest.main()
