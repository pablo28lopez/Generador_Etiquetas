import os
import sys
import unittest
import io
import json
import zipfile
import urllib.request
import urllib.parse

# Asegurar importación de web
sys.path.insert(0, os.path.abspath('web'))
import main


class TestWebLabelGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        main.load_catalog()

    def test_01_catalog_loaded(self):
        self.assertGreater(len(main.catalog_cache), 1000)
        stats = main.get_catalog_stats()
        self.assertGreater(stats["total_items"], 1000)
        self.assertTrue(stats["exists"])
        print(f"[TEST 1 OK] Catálogo en memoria: {len(main.catalog_cache)} artículos únicos.")

    def test_02_catalog_search(self):
        # Búsqueda por código
        items = main.search_catalog(q="01390006")
        self.assertGreater(len(items), 0)
        self.assertEqual(items[0]["item"], "01390006N")

        # Búsqueda por descripción
        items_desc = main.search_catalog(q="ABRAZADERA")
        self.assertGreater(len(items_desc), 0)
        self.assertTrue(any("ABRAZADERA" in it["description"].upper() for it in items_desc))
        print(f"[TEST 2 OK] Búsqueda por código ({len(items)} res) y descripción ({len(items_desc)} res).")

    def test_03_barcode_generation(self):
        for code in ["01390006N", "1234", "A-B-C", "SPECIAL_#1"]:
            img = main.generate_barcode_image(code, (608, 120))
            self.assertEqual(img.size, (608, 120))
        print("[TEST 3 OK] Generación de códigos de barra Code39/Code128 superada.")

    def test_04_label_generation_margins(self):
        # Etiqueta chica (620x290)
        img = main.create_label_image("01390006N", "ABRAZADERA CREMALLERA", size="60x30")
        self.assertEqual(img.size, (620, 290))

        # Etiqueta grande (1000x620)
        img_lg = main.create_label_image("01390006N", "ABRAZADERA CREMALLERA", size="60x95")
        self.assertEqual(img_lg.size, (1000, 620))
        print(f"[TEST 4 OK] Etiquetas renderizadas con éxito: chica={img.size}, grande={img_lg.size}.")

    def test_05_generate_pdf_endpoint(self):
        req = main.GeneratePdfRequest(
            items=[
                main.ItemRequest(item="01390006N", description="ABRAZADERA CREMALLERA", qty=2),
                main.ItemRequest(item="01000006N", description="Delta HMI DOP-107EG", qty=1)
            ],
            size="60x30",
            filename="TestEtiquetas"
        )
        res = main.generate_pdf(req)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.media_type, "application/pdf")
        print("[TEST 5 OK] Endpoint generate_pdf validado.")

    def test_06_print_html_endpoint(self):
        req = main.GeneratePdfRequest(
            items=[
                main.ItemRequest(item="01390006N", description="ABRAZADERA CREMALLERA", qty=1)
            ],
            size="60x30"
        )
        res = main.generate_print_html(req)
        self.assertEqual(res.status_code, 200)
        html = res.body.decode("utf-8")
        self.assertIn("62mm 29mm", html)
        self.assertIn("label-page", html)
        self.assertIn("window.print()", html)
        print("[TEST 6 OK] Documento HTML térmico con directivas @page Brother generado.")

    def test_07_download_zip_endpoint(self):
        req = main.GeneratePdfRequest(
            items=[
                main.ItemRequest(item="01390006N", description="ABRAZADERA CREMALLERA", qty=1)
            ],
            size="60x30"
        )
        res = main.download_zip(req)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.media_type, "application/zip")
        print("[TEST 7 OK] Archivo ZIP validado.")

    def test_08_health_check(self):
        h = main.health()
        self.assertEqual(h["status"], "ok")
        self.assertEqual(h["version"], main.app.version)
        print(f"[TEST 8 OK] Health check activo: versión {h['version']}.")

    def test_09_printers_endpoint(self):
        res = main.get_printers()
        self.assertIn("all_printers", res)
        self.assertIn("raw_engine_ready", res)
        self.assertTrue(res["raw_engine_ready"])
        print(f"[TEST 9 OK] Detección de impresoras validada (Total detectadas: {len(res['all_printers'])}).")

    def test_10_raster_conversion(self):
        img = main.create_label_image("01390006N", "ABRAZADERA CREMALLERA", size="60x30")
        raw_bytes = main.convert_images_to_brother_raster([img], size="60x30", roll_type="auto")
        self.assertGreater(len(raw_bytes), 1000)
        # Comprobar inicio del comando ESC i a 1 (Raster mode)
        self.assertTrue(raw_bytes.startswith(b"\x1bia\x01") or b"\x1bia\x01" in raw_bytes[:100])
        print(f"[TEST 10 OK] Generación de bytecode raster Brother QL superada ({len(raw_bytes)} bytes).")

    def test_11_download_prn_endpoint(self):
        req = main.PrintBrotherRawRequest(
            items=[
                main.ItemRequest(item="01390006N", description="ABRAZADERA CREMALLERA", qty=1)
            ],
            size="60x30",
            roll_type="auto"
        )
        res = main.download_prn(req)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.media_type, "application/octet-stream")
        self.assertGreater(len(res.body), 1000)
        print(f"[TEST 11 OK] Endpoint download_prn validado ({len(res.body)} bytes).")

    def test_12_generate_test_label_image(self):
        test_img = main.generate_test_label_image("TEST-HOST", "Brother QL-800")
        self.assertIsNotNone(test_img)
        self.assertEqual(test_img.size, (620, 290))
        raw_bytes = main.convert_images_to_brother_raster([test_img], size="60x30", roll_type="continuous")
        self.assertGreater(len(raw_bytes), 1000)
        print(f"[TEST 12 OK] Etiqueta de test para botón de prueba validada ({len(raw_bytes)} bytes).")


if __name__ == "__main__":
    unittest.main()

