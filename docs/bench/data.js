window.BENCHMARK_DATA = {
  "lastUpdate": 1773859912908,
  "repoUrl": "https://github.com/bitflight-devops/skilllint",
  "entries": {
    "Benchmark": [
      {
        "commit": {
          "author": {
            "name": "Jamie McGregor Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "committer": {
            "name": "Jamie McGregor Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "id": "97def80d24e767b6a6594b2b2b2e47fd425ebf8b",
          "message": "fix(ci): switch benchmark-action to auto-push, remove broken manual commit step\n\nThe manual 'Commit updated benchmark data' step was using\n'git push origin HEAD' to push docs/bench/ to the current branch,\nbut with auto-push:false the action writes data to gh-pages locally\n(not the main working tree), so 'git add docs/bench/' always found\nnothing and the push was a no-op at best.\n\nFix: set auto-push:true on all three Store steps so the action\nmanages its own gh-pages commit/push atomically. Remove the now-\nredundant manual commit step from both benchmark-io and\nbenchmark-release jobs.",
          "timestamp": "2026-03-18T18:50:35Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/97def80d24e767b6a6594b2b2b2e47fd425ebf8b"
        },
        "date": 1773859871123,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "cpu_clean_mean_ms",
            "value": 0.532482,
            "unit": "ms"
          },
          {
            "name": "cpu_violations_mean_ms",
            "value": 0.721954,
            "unit": "ms"
          },
          {
            "name": "cpu_fix_mean_ms",
            "value": 1.865923,
            "unit": "ms"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "name": "Jamie McGregor Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "committer": {
            "name": "Jamie McGregor Nelson",
            "username": "Jamie-BitFlight",
            "email": "jamie@bitflight.io"
          },
          "id": "97def80d24e767b6a6594b2b2b2e47fd425ebf8b",
          "message": "fix(ci): switch benchmark-action to auto-push, remove broken manual commit step\n\nThe manual 'Commit updated benchmark data' step was using\n'git push origin HEAD' to push docs/bench/ to the current branch,\nbut with auto-push:false the action writes data to gh-pages locally\n(not the main working tree), so 'git add docs/bench/' always found\nnothing and the push was a no-op at best.\n\nFix: set auto-push:true on all three Store steps so the action\nmanages its own gh-pages commit/push atomically. Remove the now-\nredundant manual commit step from both benchmark-io and\nbenchmark-release jobs.",
          "timestamp": "2026-03-18T18:50:35Z",
          "url": "https://github.com/bitflight-devops/skilllint/commit/97def80d24e767b6a6594b2b2b2e47fd425ebf8b"
        },
        "date": 1773859912556,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "scan_min_ms",
            "value": 9048.378,
            "unit": "ms"
          },
          {
            "name": "scan_mean_ms",
            "value": 9106.586,
            "unit": "ms"
          },
          {
            "name": "scan_max_ms",
            "value": 9172.34,
            "unit": "ms"
          },
          {
            "name": "files_per_second",
            "value": 109.92,
            "unit": "files/s"
          }
        ]
      }
    ]
  }
}