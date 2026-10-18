# Tasks 008

- [X] T1 `FIRESTORE_DATABASE` setting through config, both factories and both Firestore repositories
- [X] T2 Terraform rewrite for mananutils: APIs, named DB, Artifact Registry, secrets, runtime + deploy SAs (shared WIF), Cloud Run, public invoker, scheduler, Hosting site + rewrite; state in the shared bucket; `import.sh` removed
- [X] T3 `.github/workflows/deploy.yml` (tag → import check → build/push → deploy → `/health`)
- [X] T4 Docs: terraform/README (runbook), DEPLOYMENT.md note, Project_Structure changelog; firebase.json/.firebaserc → mananutils
- [X] T5 Bruno gate (local, SQLite + mock): 97 requests, 242/242 assertions pass
- [ ] T6 Director: secrets bootstrap + copy values; OAuth client; full `terraform apply`
- [ ] T7 Director: data export/import; GitHub variables; first `v*` tag deploy
- [ ] T8 Verify success criteria; pause old scheduler; delete project `cheapsawari`
