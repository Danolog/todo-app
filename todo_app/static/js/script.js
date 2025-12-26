document.addEventListener('DOMContentLoaded', () => {
    const taskInput = document.getElementById('task-input');
    const addBtn = document.getElementById('add-btn');
    const taskList = document.getElementById('task-list');
    const dateDisplay = document.getElementById('date-display');

    // Set date
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    dateDisplay.textContent = new Date().toLocaleDateString('en-US', options);

    // Add task
    async function addTask() {
        const title = taskInput.value.trim();
        if (!title) return;

        try {
            const response = await fetch('/api/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title })
            });

            if (response.ok) {
                const task = await response.json();
                renderTask(task);
                taskInput.value = '';
                taskInput.focus();
            }
        } catch (error) {
            console.error('Error adding task:', error);
        }
    }

    // Toggle task
    async function toggleTask(id, element) {
        try {
            const response = await fetch(`/api/tasks/${id}`, { method: 'PUT' });
            if (response.ok) {
                element.classList.toggle('completed');
            }
        } catch (error) {
            console.error('Error toggling task:', error);
        }
    }

    // Delete task
    async function deleteTask(id, element) {
        try {
            const response = await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
            if (response.ok) {
                element.style.transform = 'translateX(20px)';
                element.style.opacity = '0';
                setTimeout(() => {
                    element.remove();
                }, 300);
            }
        } catch (error) {
            console.error('Error deleting task:', error);
        }
    }

    // Render single task
    function renderTask(task) {
        const li = document.createElement('li');
        li.className = `task-item ${task.is_complete ? 'completed' : ''}`;
        li.dataset.id = task.id;

        li.innerHTML = `
            <div class="task-content">
                <div class="checkbox"></div>
                <span>${task.title}</span> <!-- Potential XSS if not escaped, but innerText/textContent is safer usually. Flask templates auto-escape, here we use JS. -->
            </div>
            <button class="delete-btn">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
            </button>
        `;

        // Security note: In a real app, use textContent for user input to avoid XSS. 
        // Let's fix the span content to be safe.
        const span = li.querySelector('span');
        span.textContent = task.title;

        taskList.appendChild(li);
        attachEvents(li, task.id);
    }

    function attachEvents(li, id) {
        const content = li.querySelector('.task-content');
        const deleteBtn = li.querySelector('.delete-btn');

        content.addEventListener('click', () => toggleTask(id, li));
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteTask(id, li);
        });
    }

    // Attach events to existing tasks (SSR)
    document.querySelectorAll('.task-item').forEach(li => {
        const id = li.dataset.id;
        attachEvents(li, id);
    });

    addBtn.addEventListener('click', addTask);
    taskInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') addTask();
    });
});
