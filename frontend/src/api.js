const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export function fetchWithProject(path, options = {}, projectSlug) {
  const url = new URL(path, API_BASE_URL);
  if (projectSlug) {
    url.searchParams.set('project_slug', projectSlug);
  }
  return fetch(url.toString(), options);
}

export { API_BASE_URL };
