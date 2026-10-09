FIRST 1000: ADD THE MISSING GITHUB DEPLOYMENT FILES

This package contains the original app and its original .github and
.gitignore files. The GITHUB_UPLOAD folder also contains visible copies
so you can upload them without showing hidden files in Finder.

Your application files are already uploaded to GitHub. Use only the two
files below to finish the existing repository; keep the uploaded app.

1. Extract First1000-GitHub.zip and open first1000/GITHUB_UPLOAD.
2. On GitHub, open your first1000 repository's Code tab.
3. Click Add file > Upload files.
4. Drag pages.yml and gitignore.txt from GITHUB_UPLOAD into the upload area.
   Upload these TWO FILES directly, rather than their containing folder.
5. Enter Add deployment files, commit directly to main, and commit changes.
6. Click pages.yml in the repository, then the pencil / Edit this file button.
7. Change its filename to .github/workflows/pages.yml and commit to main.
   Typing each slash creates the matching folder in GitHub's editor.
8. Return to Code, open gitignore.txt, and click the pencil / Edit this file.
9. Change its filename to .gitignore and commit to main.
10. Open Settings > Pages. Under Source, choose GitHub Actions.
11. Open Actions > Deploy Flet web app > Run workflow.
12. Select main and click the green Run workflow button.
13. Wait for a green checkmark, then open Settings > Pages > Visit site.

After the moves, these exact files must exist at the repository root:
  .github/workflows/pages.yml
  .gitignore

GitHub recognizes workflows only in .github/workflows. The visible copy
pages.yml at the repository root will not deploy until you move it there.

If a run fails, open the failed job and copy the failed step's error text.
The application source and curriculum are identical to the original ZIP.
