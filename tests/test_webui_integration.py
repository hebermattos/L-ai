"""Opt-in integration test: disposable local Knowledge Base required."""
import os
import uuid
import unittest
from ingest.webui import WebUI

@unittest.skipUnless(os.getenv("L_AI_INTEGRATION")=="1","Requires local Open WebUI and opt-in")
class LiveWebUIIntegration(unittest.TestCase):
    def test_upload_process_link_update(self):
        api = WebUI("http://127.0.0.1:3000",os.environ["OPEN_WEBUI_API_KEY"],
                    os.environ["OPEN_WEBUI_KNOWLEDGE_ID"])
        token = uuid.uuid4().hex
        original = "# Live integration\n\n" + ("Original passage "+token+"\n")*30
        changed = "# Live integration\n\n" + ("Revised passage "+token+"\n")*30
        file_id = api.upload("integration-"+token+".md",original)
        api.wait_indexed(file_id)
        api.ensure_linked(file_id)
        self.assertTrue(api.knowledge_has_file(file_id))
        api.update_content(file_id,changed)
        api.verify_content(file_id,changed)
        # Intentionally no deletion: requires explicit disposable KB.
