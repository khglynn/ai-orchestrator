const STORAGE_KEY = 'resume-data-v1';

const state = {
  data: null,
  editMode: false,
  variant: null,
};

function loadDefaultData() {
  return fetch('data/resume.json').then((resp) => resp.json());
}

function loadStoredData() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (!saved) return null;
  try {
    return JSON.parse(saved);
  } catch (err) {
    console.warn('Could not parse stored data, falling back to defaults', err);
    return null;
  }
}

function saveData() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    variant: state.variant,
    data: state.data,
  }));
}

function createEditable(tag, text, path, className = '') {
  const el = document.createElement(tag);
  el.textContent = text;
  el.dataset.path = path;
  el.dataset.editable = 'true';
  if (className) el.className = className;
  return el;
}

function setValueAtPath(obj, path, value) {
  const steps = path.split('.');
  let current = obj;
  for (let i = 0; i < steps.length - 1; i += 1) {
    current = current[steps[i]];
  }
  current[steps.at(-1)] = value;
}

function handleEdit(event) {
  const target = event.target;
  if (target.dataset.editable !== 'true') return;
  const path = target.dataset.path;
  setValueAtPath(state.data, path, target.textContent.trim());
  saveData();
}

function buildContact(contact) {
  const container = document.createElement('div');
  container.className = 'contact';

  contact.lines.forEach((text, index) => {
    const p = createEditable('div', text, `contact.lines.${index}`, 'contact__line');
    container.appendChild(p);
  });

  return container;
}

function buildTags(tags, pathPrefix) {
  const tagContainer = document.createElement('div');
  tagContainer.className = 'tags';
  tags.forEach((tag, index) => {
    const span = createEditable('span', tag, `${pathPrefix}.${index}`, 'tag');
    tagContainer.appendChild(span);
  });
  return tagContainer;
}

function buildList(items, pathPrefix) {
  const list = document.createElement('div');
  list.className = 'list';

  items.forEach((item, index) => {
    const wrapper = document.createElement('div');

    const title = createEditable('h4', item.title, `${pathPrefix}.${index}.title`, 'list__item-title');
    const meta = document.createElement('div');
    meta.className = 'list__item-meta';
    const location = createEditable('span', item.location, `${pathPrefix}.${index}.location`);
    const period = createEditable('span', item.period, `${pathPrefix}.${index}.period`);
    meta.append(location, period);

    wrapper.append(title, meta);

    if (item.bullets && item.bullets.length) {
      const bullets = document.createElement('ul');
      bullets.className = 'bullets';
      item.bullets.forEach((bullet, bulletIndex) => {
        const li = document.createElement('li');
        const bulletEl = createEditable('span', bullet, `${pathPrefix}.${index}.bullets.${bulletIndex}`);
        li.appendChild(bulletEl);
        bullets.appendChild(li);
      });
      wrapper.appendChild(bullets);
    }

    if (item.tags && item.tags.length) {
      wrapper.appendChild(buildTags(item.tags, `${pathPrefix}.${index}.tags`));
    }

    list.appendChild(wrapper);
  });

  return list;
}

function buildSection(title, contentEl, className = '') {
  const section = document.createElement('section');
  section.className = `section ${className}`;

  const heading = document.createElement('h3');
  heading.className = 'section__title';
  heading.textContent = title;
  section.appendChild(heading);
  section.appendChild(contentEl);
  return section;
}

function buildSummary(text, path) {
  const p = createEditable('p', text, path, 'section__content');
  return p;
}

function buildPage(content, pageIndex) {
  const page = document.createElement('article');
  page.className = 'page';

  const header = document.createElement('div');
  header.className = 'page__header';
  const title = createEditable('h1', content.name, 'name', 'page__title');
  const role = createEditable('div', content.role, 'role', 'page__role');
  const titleBlock = document.createElement('div');
  titleBlock.append(title, role);

  const contact = buildContact(content.contact);
  header.append(titleBlock, contact);
  page.appendChild(header);

  const grid = document.createElement('div');
  grid.className = 'grid';

  if (pageIndex === 0) {
    const summary = buildSection('Profile', buildSummary(content.summary, 'summary'));
    summary.classList.add('full-width');
    grid.appendChild(summary);

    const skills = buildSection('Skills', buildTags(content.skills, 'skills'));
    grid.appendChild(skills);

    const experience = buildSection('Experience', buildList(content.experience.slice(0, 3), 'experience'));
    experience.classList.add('full-width');
    grid.appendChild(experience);
  } else {
    const additional = buildSection('Experience Continued', buildList(content.experience.slice(3), 'experience'));
    additional.classList.add('full-width');
    grid.appendChild(additional);

    const projects = buildSection('Projects', buildList(content.projects, 'projects'));
    projects.classList.add('full-width');
    grid.appendChild(projects);

    const education = buildSection('Education', buildList(content.education, 'education'));
    education.classList.add('full-width');
    grid.appendChild(education);
  }

  page.appendChild(grid);

  const notice = document.createElement('div');
  notice.className = 'notice';
  notice.textContent = 'Enable editing to click any text, update it in place, and keep changes in this browser.';
  page.appendChild(notice);

  const footer = document.createElement('footer');
  footer.textContent = 'Two-page layout is print ready. Use the browser print dialog to export to PDF or paper.';
  page.appendChild(footer);

  return page;
}

function render() {
  const container = document.getElementById('resume');
  container.classList.toggle('edit-mode', state.editMode);
  container.innerHTML = '';

  const page1 = buildPage(state.data, 0);
  const page2 = buildPage(state.data, 1);
  container.append(page1, page2);

  const editables = container.querySelectorAll('[data-editable="true"]');
  editables.forEach((el) => {
    el.contentEditable = state.editMode;
    el.removeEventListener('input', handleEdit);
    if (state.editMode) {
      el.addEventListener('input', handleEdit);
    }
  });

  const toggleEdit = document.getElementById('toggle-edit');
  toggleEdit.textContent = state.editMode ? 'Disable editing' : 'Enable editing';
}

function applyVariant(variantName, variants) {
  state.variant = variantName;
  state.data = JSON.parse(JSON.stringify(variants[variantName]));
  saveData();
  render();
}

async function init() {
  const defaults = await loadDefaultData();
  const stored = loadStoredData();

  const activeVariant = stored?.variant || defaults.defaultVariant;
  const baseData = stored?.data || defaults.variants[activeVariant];

  state.variant = activeVariant;
  state.data = JSON.parse(JSON.stringify(baseData));

  const resume = document.getElementById('resume');
  resume.addEventListener('click', (event) => {
    if (!state.editMode) return;
    if (event.target.dataset.editable === 'true') {
      event.target.focus();
    }
  });

  document.getElementById('toggle-edit').addEventListener('click', () => {
    state.editMode = !state.editMode;
    render();
  });

  document.getElementById('reset-content').addEventListener('click', () => {
    applyVariant(defaults.defaultVariant, defaults.variants);
  });

  document.getElementById('print').addEventListener('click', () => window.print());

  render();
}

init();
