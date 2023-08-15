import unittest
import tempfile
import os
import codecs

from storage import FileSystem


class TestFileSystem(unittest.TestCase):
    def test_constructor_without_groups_list(self):
        storage_dir = tempfile.mkdtemp()

        _ = FileSystem(storage_dir)

        self.assertEqual([], list(os.scandir(storage_dir)))

    def test_constructor_with_groups_list(self):
        storage_dir = tempfile.mkdtemp()

        _ = FileSystem(storage_dir, ("1",))

        dirs_to_be_created = [
            storage_dir + os.path.sep + "1",
            storage_dir + os.path.sep + "1" + os.path.sep + "confirm_codes",
            storage_dir + os.path.sep + "1" + os.path.sep + "confirmed",
        ]

        for d in dirs_to_be_created:
            self.assertTrue(
                os.path.exists(d),
                f"no subdirectory created: {d}",
            )

        self.assertFalse(os.path.exists(storage_dir + os.path.sep + "groups.txt"))

    def test_constructor_with_groups_list_txt(self):
        storage_dir = tempfile.mkdtemp()

        with open(os.path.sep.join([storage_dir, "groups.txt"]), "w") as f:
            f.write("1")

        _ = FileSystem(storage_dir)

        self.assertTrue(os.path.exists(storage_dir + os.path.sep + "groups.txt"))

        dirs_to_be_created = [
            os.path.sep.join([storage_dir, "1"]),
            os.path.sep.join([storage_dir, "1", "confirm_codes"]),
            os.path.sep.join([storage_dir, "1", "confirmed"]),
        ]

        for d in dirs_to_be_created:
            self.assertTrue(
                os.path.exists(d),
                f"no subdirectory created: {d}",
            )

    def test_is_user_confirmed_false(self):
        storage_dir = tempfile.mkdtemp()

        with open(os.path.sep.join([storage_dir, "groups.txt"]), "w") as f:
            f.write("1")

        fs = FileSystem(storage_dir)

        self.assertFalse(fs.is_user_confirmed(1, 1))

    def test_is_user_confirmed_true(self):
        storage_dir = tempfile.mkdtemp()

        with open(os.path.sep.join([storage_dir, "groups.txt"]), "w") as f:
            f.write("1")

        fs = FileSystem(storage_dir)

        with open(os.path.sep.join([storage_dir, "1", "confirmed", "1"]), "w") as f:
            f.write("1")

        self.assertTrue(fs.is_user_confirmed(1, 1))

    def test_set_user_confirmed(self):
        storage_dir = tempfile.mkdtemp()

        with open(os.path.sep.join([storage_dir, "groups.txt"]), "w") as f:
            f.write("1")

        fs = FileSystem(storage_dir)

        self.assertFalse(fs.is_user_confirmed(1, 1))

        fs.set_user_confirmed(1, 1)

        self.assertTrue(fs.is_user_confirmed(1, 1))

    def test_set_user_confirm_code(self):
        storage_dir = tempfile.mkdtemp()

        with open(os.path.sep.join([storage_dir, "groups.txt"]), "w") as f:
            f.write("1")

        fs = FileSystem(storage_dir)

        self.assertFalse(os.path.exists(os.path.sep.join([storage_dir, "1", "confirm_codes", "1"])))
        self.assertIsNone(fs.set_user_confirm_code(1, 1, "❤️"))
        self.assertTrue(os.path.exists(os.path.sep.join([storage_dir, "1", "confirm_codes", "1"])))

        with codecs.open(os.path.sep.join([storage_dir, "1", "confirm_codes", "1"]), "r", encoding="utf-8") as f:
            self.assertEqual("❤️", f.read())

    def test_get_user_confirm_code(self):
        storage_dir = tempfile.mkdtemp()

        with open(os.path.sep.join([storage_dir, "groups.txt"]), "w") as f:
            f.write("1")

        fs = FileSystem(storage_dir)

        self.assertIsNone(fs.get_user_confirm_code(1, 1))

        with codecs.open(os.path.sep.join([storage_dir, "1", "confirm_codes", "1"]), "w", encoding="utf-8") as f:
            f.write("❤️")

        self.assertEqual("❤️", fs.get_user_confirm_code(1, 1))

    def test_on_added_to_group_first_time(self):
        storage_dir = tempfile.mkdtemp()

        fs = FileSystem(storage_dir)
        fs.on_added_to_group(2)

        dirs_to_be_created = [
            os.path.sep.join([storage_dir, "2"]),
            os.path.sep.join([storage_dir, "2", "confirm_codes"]),
            os.path.sep.join([storage_dir, "2", "confirmed"]),
        ]

        for d in dirs_to_be_created:
            self.assertTrue(
                os.path.exists(d),
                f"no subdirectory created: {d}",
            )

        with open(os.path.sep.join([storage_dir, "groups.txt"]), "r") as f:
            self.assertEqual([2], [int(x) for x in f.readlines()])

    def test_on_added_to_group_when_another_exists(self):
        storage_dir = tempfile.mkdtemp()

        fs = FileSystem(storage_dir, ("1",))
        fs.on_added_to_group(2)

        dirs_to_be_created = [
            os.path.sep.join([storage_dir, "2"]),
            os.path.sep.join([storage_dir, "2", "confirm_codes"]),
            os.path.sep.join([storage_dir, "2", "confirmed"]),
        ]

        for d in dirs_to_be_created:
            self.assertTrue(
                os.path.exists(d),
                f"no subdirectory created: {d}",
            )

        with open(os.path.sep.join([storage_dir, "groups.txt"]), "r") as f:
            groups = [int(x) for x in f.readlines()]
            self.assertIn(1, groups)
            self.assertIn(2, groups)
