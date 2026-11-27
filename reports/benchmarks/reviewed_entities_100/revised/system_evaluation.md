# ActivIQ system evaluation

Run: 2026-11-09T17:24:35.657910+00:00

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
      "tp": 145,
      "fp": 20,
      "fn": 36,
      "support": 181,
      "precision": 0.8787878787878788,
      "recall": 0.8011049723756906,
      "f1": 0.838150289017341
    },
    "macro_f1": 0.8602324903924858,
    "exact_match_rate": 0.66,
    "per_slot": {
      "exercise": {
        "tp": 13,
        "fp": 12,
        "fn": 19,
        "support": 32,
        "precision": 0.52,
        "recall": 0.40625,
        "f1": 0.45614035087719296
      },
      "body_part": {
        "tp": 29,
        "fp": 2,
        "fn": 3,
        "support": 32,
        "precision": 0.9354838709677419,
        "recall": 0.90625,
        "f1": 0.9206349206349206
      },
      "equipment": {
        "tp": 26,
        "fp": 3,
        "fn": 6,
        "support": 32,
        "precision": 0.896551724137931,
        "recall": 0.8125,
        "f1": 0.8524590163934426
      },
      "goal": {
        "tp": 14,
        "fp": 0,
        "fn": 2,
        "support": 16,
        "precision": 1.0,
        "recall": 0.875,
        "f1": 0.9333333333333333
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
        "tp": 16,
        "fp": 2,
        "fn": 1,
        "support": 17,
        "precision": 0.8888888888888888,
        "recall": 0.9411764705882353,
        "f1": 0.9142857142857143
      },
      "food": {
        "tp": 14,
        "fp": 0,
        "fn": 5,
        "support": 19,
        "precision": 1.0,
        "recall": 0.7368421052631579,
        "f1": 0.8484848484848485
      },
      "nutrient": {
        "tp": 22,
        "fp": 0,
        "fn": 0,
        "support": 22,
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0
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
  "git_commit": "046368ba3bec2af549ca53745f91048cde56b65d",
  "git_tracked_changes": "",
  "startup_seconds_this_process": 2.080460600089282,
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
    "scripts\\auto_label.py": "dc5fcc25e4278c380fdb9bdd6f31f346121e7d680bae177f11345579739c330b",
    "scripts\\evaluate_intent.py": "781b1dfb68608ab18b2c98ee8116f51c44f97ca08cc5c205fff75cb88dcb0b4f",
    "scripts\\evaluate_lora.py": "524f526846272722a60bd2895ec4a463e1e808301ee584297c9eb8c840b8f5e5",
    "scripts\\evaluate_system.py": "be15351ad82fa80e1b63ce0b5da4089b232dbfcd712b47ac13330e8bde323482",
    "scripts\\prepare_autolabelling.py": "03e38ae684cfaa9d31130cab6fedca6a54ae1ac89adf92c6bae05d5ce0468716",
    "scripts\\prepare_data.py": "c3a8f7bd6040b1399c3e2f1382ca4583bd5981ff8ad6197d9a9c3b5faadc5f8c",
    "scripts\\prepare_entity_annotations.py": "edeea5d7fbfd72091f5419dfae895cc55a00488b2c9c82ec5e93466ab1997ac4",
    "scripts\\sign_off_annotations.py": "bcbd9cdc35c33d29ebd9043531f6bd5ffad8cbed75e6c180b07ea77a249514f9",
    "scripts\\train_intent.py": "b64419ca31ecd64194d155d1c3760b1eb627a10b2708fef0c4a1cbf72868b402",
    "scripts\\train_lora.py": "214bcca57921da7dc185b0da5866137a92f06ae6324f79c7d754343d62fdda55",
    "src\\__init__.py": "57ffe2f0328ef227437cec3bf18a2e3c0d1315c0cac6b6eca094f07097d6cd8d",
    "src\\config.py": "62ae5117efe8c88045242b0a90642b1aa5152630e3393e0edf41cf30cf80cae7",
    "src\\dialogue_manager.py": "9612ab10669ddf523e8300784eac14e1fc8b8ea03b8fcccafb06c7e4009634c8",
    "src\\entity_extractor.py": "1f3fb8598e519e64f028e19951a7eb4dc81c14a2b0bcf20b0888414e552e5ade",
    "src\\evaluation.py": "29786a395b6d4329aa11a000e66e3123a15982f2c39e60659d48db501e0f3584",
    "src\\intent_classifier.py": "1d518829c248e6bda0205078d21a4c95db2ff3eb294671e4740711285d8ad44e",
    "src\\knowledge_base.py": "93aee804fa93041e26006676b7846357345329414c319dab9fb007d90efa5025",
    "src\\lora.py": "1f128d64a21ec5d1abbca47ced80a3547c193d521de6de2394afe209df701d2d",
    "src\\nutrition.py": "33eae26fdd4961916068a2effd60abd2709d57a87823fa64641571568f1da7af",
    "src\\pipeline.py": "1124e65224a5c48676c5f86391121782665cb86386a24fd29b36011b17d64ab1",
    "src\\planner.py": "91f2a14671adc21948d287300497d602dbe84a3a2e086265d0b090a183aca368",
    "src\\response_generator.py": "3625a40c2fd6af6827723b13682e7eb738c9ab6573fc0c85f1068f6e8cc30688",
    "src\\safety.py": "5c1eeb496f0d2a40698bebbf0aaf0b3e5015f47ca897a7b8c1db5586e8afaa69",
    "src\\scope.py": "bad199480e49ef5788a9e042e039bfc757ec6ed7f38890dd880d940833ccc19a",
    "src\\vocabulary.py": "c4d730f6a234a2a7cbd8c502451bf1a0544180246e80f0ed0272083a16e63c5b"
  },
  "requirements_sha256": "d7ef075aac352956a612666168a245ae668956abbae8e53f642261f87175a633",
  "data_sha256": {
    "exercises.json": "3a0d0360d4e925a24b049e28d977652ad27c75f1fd34220e6a32631da8f23997",
    "nutrition.json": "7140ffe3751dec96fcc52dae07be37cb55dee371cf63c25d6d6e02f369457542"
  },
  "model_sha256": {}
}
```
