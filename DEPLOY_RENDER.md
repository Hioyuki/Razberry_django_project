# Deploy on Render

1. Push this repository to GitHub.
2. Open Render dashboard and choose **New +** -> **Blueprint**.
3. Select this repository. Render will detect `render.yaml`.
4. Click deploy.
5. After deploy is finished, your app URL is shown in Render (example: `https://razberry-django-project.onrender.com`).

## Important notes

- This project has Raspberry Pi camera endpoints. On Render, those routes will not work because there is no Pi camera device.
- Face analysis may take time on first request because model initialization is heavy.
- If your Render service name is different, update these env vars in `render.yaml`:
  - `DJANGO_ALLOWED_HOSTS`
  - `DJANGO_CSRF_TRUSTED_ORIGINS`
