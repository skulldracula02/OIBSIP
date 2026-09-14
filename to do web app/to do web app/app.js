const STORAGE_KEY = 'todoApp.tasks'

let tasks = []

// DOM refs
const taskInput = document.getElementById('taskInput')
const addBtn = document.getElementById('addBtn')
const pendingList = document.getElementById('pendingList')
const completedList = document.getElementById('completedList')
const pendingCount = document.getElementById('pendingCount')
const completedCount = document.getElementById('completedCount')
const pendingEmpty = document.getElementById('pendingEmpty')
const completedEmpty = document.getElementById('completedEmpty')

function save(){
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks))
}

function load(){
  const raw = localStorage.getItem(STORAGE_KEY)
  if(raw){
    try { tasks = JSON.parse(raw) } catch(e){ tasks = [] }
  }
}

function createTaskElement(task){
  const li = document.createElement('li')
  li.className = 'task-item'
  li.dataset.id = task.id

  const body = document.createElement('div')
  body.className = 'task-body'

  const toggle = document.createElement('button')
  toggle.className = 'btn btn-toggle'
  toggle.textContent = task.completedAt ? 'Undo' : 'Done'
  toggle.setAttribute('aria-label','Toggle complete')

  const text = document.createElement('span')
  text.className = 'task-text'
  text.textContent = task.text

  const meta = document.createElement('div')
  meta.className = 'meta'
  const created = new Date(task.createdAt).toLocaleString()
  meta.textContent = task.completedAt ? `Added ${created} • Completed ${new Date(task.completedAt).toLocaleString()}` : `Added ${created}`

  body.appendChild(toggle)
  body.appendChild(text)

  const actions = document.createElement('div')
  actions.className = 'actions'

  const editBtn = document.createElement('button')
  editBtn.className = 'btn btn-edit'
  editBtn.textContent = 'Edit'

  const delBtn = document.createElement('button')
  delBtn.className = 'btn btn-delete'
  delBtn.textContent = 'Delete'

  actions.appendChild(editBtn)
  actions.appendChild(delBtn)

  li.appendChild(body)
  li.appendChild(meta)
  li.appendChild(actions)

  return li
}

function render(){
  pendingList.innerHTML = ''
  completedList.innerHTML = ''

  const pending = tasks.filter(t => !t.completedAt)
  const completed = tasks.filter(t => t.completedAt)

  pending.forEach(t => pendingList.appendChild(createTaskElement(t)))
  completed.forEach(t => completedList.appendChild(createTaskElement(t)))

  pendingCount.textContent = pending.length
  completedCount.textContent = completed.length

  pendingEmpty.style.display = pending.length ? 'none' : 'block'
  completedEmpty.style.display = completed.length ? 'none' : 'block'
}

function addTask(text){
  const t = { id: `${Date.now()}-${Math.random().toString(36).slice(2,8)}`, text: text.trim(), createdAt: Date.now(), completedAt: null }
  tasks.unshift(t)
  save()
  render()
}

function deleteTask(id){
  tasks = tasks.filter(t => t.id !== id)
  save()
  render()
}

function toggleTask(id){
  tasks = tasks.map(t => {
    if(t.id !== id) return t
    if(t.completedAt) t.completedAt = null
    else t.completedAt = Date.now()
    return t
  })
  save()
  render()
}

function startEdit(id, li){
  const textSpan = li.querySelector('.task-text')
  const old = textSpan.textContent
  const input = document.createElement('input')
  input.type = 'text'
  input.value = old
  input.className = 'edit-input'

  textSpan.replaceWith(input)
  input.focus()

  function finish(saveEdit){
    const val = input.value.trim()
    if(saveEdit && val){
      tasks = tasks.map(t => t.id === id ? {...t, text: val} : t)
      save()
    }
    render()
  }

  input.addEventListener('blur', () => finish(true))
  input.addEventListener('keydown', (e) => {
    if(e.key === 'Enter') finish(true)
    if(e.key === 'Escape') finish(false)
  })
}

// Event delegation for lists
function onListClick(e){
  const li = e.target.closest('.task-item')
  if(!li) return
  const id = li.dataset.id

  if(e.target.classList.contains('btn-delete')){
    if(confirm('Delete this task?')) deleteTask(id)
    return
  }

  if(e.target.classList.contains('btn-edit')){
    startEdit(id, li)
    return
  }

  if(e.target.classList.contains('btn-toggle')){
    toggleTask(id)
    return
  }
}

addBtn.addEventListener('click', () => {
  const v = taskInput.value.trim()
  if(!v) return
  addTask(v)
  taskInput.value = ''
  taskInput.focus()
})

taskInput.addEventListener('keydown', (e) => { if(e.key === 'Enter') addBtn.click() })

pendingList.addEventListener('click', onListClick)
completedList.addEventListener('click', onListClick)

// Initialize
load()
render()
