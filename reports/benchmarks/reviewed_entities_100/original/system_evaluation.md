# ActivIQ system evaluation

Run: 2026-11-09T17:24:51.602233+00:00

Draft/development suites are provisional, not held-out performance claims. Check each component's provenance status. Entity targets require reviewed human test labels; the supplied conversation/safety cases were authored with knowledge of the implementation.

## entities

```json
{
  "status": "complete",
  "total": 100,
  "scored": 100,
  "pending_count": 0,
  "scoring": "Exact canonical values per utterance/slot; case and whitespace normalised; eight proposal slots",
  "extractor_backend": "spacy_phrase_matcher",
  "provisional": false,
  "target_f1": 0.85,
  "proposal_target_verified": false,
  "metrics": {
    "utterances": 100,
    "micro": {
      "tp": 120,
      "fp": 39,
      "fn": 61,
      "support": 181,
      "precision": 0.7547169811320755,
      "recall": 0.6629834254143646,
      "f1": 0.7058823529411765
    },
    "macro_f1": 0.7139554544972432,
    "exact_match_rate": 0.45,
    "per_slot": {
      "exercise": {
        "tp": 10,
        "fp": 10,
        "fn": 22,
        "support": 32,
        "precision": 0.5,
        "recall": 0.3125,
        "f1": 0.38461538461538464
      },
      "body_part": {
        "tp": 28,
        "fp": 2,
        "fn": 4,
        "support": 32,
        "precision": 0.9333333333333333,
        "recall": 0.875,
        "f1": 0.9032258064516129
      },
      "equipment": {
        "tp": 24,
        "fp": 3,
        "fn": 8,
        "support": 32,
        "precision": 0.8888888888888888,
        "recall": 0.75,
        "f1": 0.8135593220338984
      },
      "goal": {
        "tp": 13,
        "fp": 0,
        "fn": 3,
        "support": 16,
        "precision": 1.0,
        "recall": 0.8125,
        "f1": 0.896551724137931
      },
      "level": {
        "tp": 11,
        "fp": 1,
        "fn": 0,
        "support": 11,
        "precision": 0.9166666666666666,
        "recall": 1.0,
        "f1": 0.9565217391304348
      },
      "duration": {
        "tp": 10,
        "fp": 8,
        "fn": 7,
        "support": 17,
        "precision": 0.5555555555555556,
        "recall": 0.5882352941176471,
        "f1": 0.5714285714285714
      },
      "food": {
        "tp": 6,
        "fp": 14,
        "fn": 13,
        "support": 19,
        "precision": 0.3,
        "recall": 0.3157894736842105,
        "f1": 0.3076923076923077
      },
      "nutrient": {
        "tp": 18,
        "fp": 1,
        "fn": 4,
        "support": 22,
        "precision": 0.9473684210526315,
        "recall": 0.8181818181818182,
        "f1": 0.8780487804878049
      }
    },
    "covered_slots": [
      "exercise",
      "body_part",
      "equipment",
      "goal",
      "level",
      "duration",
      "food",
      "nutrient"
    ]
  },
  "target_met_on_scored_subset": false
}
```

## Reproducibility metadata

```json
{
  "python": "3.13.1 (tags/v3.13.1:0671451, Dec  3 2024, 19:06:28) [MSC v.1942 64 bit (AMD64)]",
  "platform": "Windows-11-10.0.26200-SP0",
  "processor": "AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD",
  "logical_cpus": 16,
  "packages": {
    "torch": "2.6.0",
    "transformers": "4.50.0",
    "spacy": "3.8.18",
    "numpy": "2.4.4"
  },
  "torch_intraop_threads": 8,
  "torch_interop_threads": 8,
  "git_commit": null,
  "git_tracked_changes": null,
  "startup_seconds_this_process": 1.528740799985826,
  "extractor_backend": "spacy_phrase_matcher",
  "classifier_device": null,
  "input_files": {
    "entities": {
      "path": "C:\\Users\\Michael\\Documents\\GitHub\\ActivIQ\\reports\\evaluation\\entity_review_packet\\entities_fresh_reviewed_frozen.jsonl",
      "sha256": "6b687dc544fe5b071caabed287cf4da94327b505525b2893abb9aa08fd6b7887"
    }
  },
  "source_sha256": {
    "scripts\\__init__.py": "0ca1aedb7042b89e33d8faac2f3126e703e69238eaa5d7b48cf01a32683d7a82",
    "scripts\\auto_label.py": "3137a30a8b7398ed0a5361f530661f5544fc85c6856521abcad532df59cabe73",
    "scripts\\evaluate_intent.py": "781b1dfb68608ab18b2c98ee8116f51c44f97ca08cc5c205fff75cb88dcb0b4f",
    "scripts\\evaluate_lora.py": "524f526846272722a60bd2895ec4a463e1e808301ee584297c9eb8c840b8f5e5",
    "scripts\\evaluate_system.py": "599fab13e78d0057f7f6a3fcf69f813a6f3d44004483adb5567fa63b8949387f",
    "scripts\\prepare_autolabelling.py": "c1c3069db1f67724ae339c63e3cb99ce7e41d31fc01a69ead8bf3bafcb0e2a9c",
    "scripts\\prepare_data.py": "c3a8f7bd6040b1399c3e2f1382ca4583bd5981ff8ad6197d9a9c3b5faadc5f8c",
    "scripts\\prepare_entity_annotations.py": "608d9e1a24bae316d7843eb56341e41702ec2c11292e44063cd552b9d5739af5",
    "scripts\\sign_off_annotations.py": "bcbd9cdc35c33d29ebd9043531f6bd5ffad8cbed75e6c180b07ea77a249514f9",
    "scripts\\train_intent.py": "b64419ca31ecd64194d155d1c3760b1eb627a10b2708fef0c4a1cbf72868b402",
    "scripts\\train_lora.py": "214bcca57921da7dc185b0da5866137a92f06ae6324f79c7d754343d62fdda55",
    "src\\__init__.py": "57ffe2f0328ef227437cec3bf18a2e3c0d1315c0cac6b6eca094f07097d6cd8d",
    "src\\config.py": "62ae5117efe8c88045242b0a90642b1aa5152630e3393e0edf41cf30cf80cae7",
    "src\\dialogue_manager.py": "3576bcf0789f2aecc3b07937ef40b0164c203b1b8dce3cb280aa7ee62a338f08",
    "src\\entity_extractor.py": "26165f3ae4942411a87c381ebee3e942c8ffd65238eb97026fe91021f12216e8",
    "src\\evaluation.py": "be283177b4fe0b70c25651603c723bf4f26834b016b4d64077bf929e20ec2e9c",
    "src\\intent_classifier.py": "1d518829c248e6bda0205078d21a4c95db2ff3eb294671e4740711285d8ad44e",
    "src\\knowledge_base.py": "93aee804fa93041e26006676b7846357345329414c319dab9fb007d90efa5025",
    "src\\lora.py": "1f128d64a21ec5d1abbca47ced80a3547c193d521de6de2394afe209df701d2d",
    "src\\nutrition.py": "8c788106e938a599b172e13ceb00dbe27bc1dc8e0da27333887a7613e6b1cd19",
    "src\\pipeline.py": "ed62e4f5b15b50e5b23fd4271436b8ad935614a37b2739619db5473b0d12821a",
    "src\\planner.py": "daa87830fc6cc5080522447cc7e1498c6667a407bdb896cd86213fd10e0aada0",
    "src\\response_generator.py": "d6d42cecd134f822543e7fb29eab40f042227c8c848cce824bbf8b07aa20772d",
    "src\\safety.py": "5c1eeb496f0d2a40698bebbf0aaf0b3e5015f47ca897a7b8c1db5586e8afaa69",
    "src\\scope.py": "7d2a1660c040040f6a1479c2c549a49bcd4864bd32e7ef801ec7bc6378963d04",
    "src\\vocabulary.py": "38875a7a4f71771dee484c7938d8458875855daebe88150f676cdd984a1cd867"
  },
  "requirements_sha256": "d7ef075aac352956a612666168a245ae668956abbae8e53f642261f87175a633",
  "data_sha256": {
    "exercises.json": "3a0d0360d4e925a24b049e28d977652ad27c75f1fd34220e6a32631da8f23997",
    "nutrition.json": "7140ffe3751dec96fcc52dae07be37cb55dee371cf63c25d6d6e02f369457542"
  },
  "model_sha256": {}
}
```
