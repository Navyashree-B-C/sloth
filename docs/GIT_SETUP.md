# Sloth – Git & GitHub setup

## SSH check

Your SSH is working with GitHub (authenticated as **Navyashree-B-C**).

To test again:
```bash
ssh -T git@github.com
# Expected: "Hi Navyashree-B-C! You've successfully authenticated..."
```

---

## 1. Create the Sloth repository on GitHub

1. Open **https://github.com/new**
2. **Repository name:** `Sloth` (or `sloth`)
3. **Visibility:** Private or Public
4. **Do not** add a README, .gitignore, or license (this project already has them).
5. Click **Create repository**.

---

## 2. Connect this project and push

Run these in the project root (`/Users/navyashreebc/Documents/projects/Sloth`):

```bash
# Initialize repo and create main branch (if not already a git repo)
git init -b main

# Stage and commit
git add .
git commit -m "Initial commit: SLOTH wake authority (frontend + backend)"

# Add GitHub remote (use your repo URL; SSH format below)
git remote add origin git@github.com:Navyashree-B-C/Sloth.git

# Push main
git push -u origin main
```

If the repo already exists and has a different remote, update it:
```bash
git remote set-url origin git@github.com:Navyashree-B-C/Sloth.git
git push -u origin main
```

---

## 3. Create and use a develop branch

```bash
# Create develop from current main
git checkout -b develop

# After making changes, commit on develop
git add .
git commit -m "Your message"

# Run tests locally (optional)
cd backend && pytest tests/ -v && cd ..
cd frontend && npm ci && npm run build && cd ..

# Merge develop into main and push
git checkout main
git merge develop
git push origin main
```

Replace `Navyashree-B-C` and `Sloth` if your GitHub username or repo name differ.
