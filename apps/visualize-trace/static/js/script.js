// SPDX-FileCopyrightText: 2025 MiromindAI
//
// SPDX-License-Identifier: Apache-2.0

// Global variables
let currentFlowData = null;
let currentBasicInfo = null;
let currentFileList = [];
let currentFileIndex = -1;

// DOM elements
const elements = {
    directoryInput: document.getElementById('directoryInput'),
    browseDirectoryBtn: document.getElementById('browseDirectoryBtn'),
    fileSelect: document.getElementById('fileSelect'),
    prevFileBtn: document.getElementById('prevFileBtn'),
    nextFileBtn: document.getElementById('nextFileBtn'),
    loadBtn: document.getElementById('loadBtn'),
    refreshBtn: document.getElementById('refreshBtn'),
    expandAllBtn: document.getElementById('expandAllBtn'),
    collapseAllBtn: document.getElementById('collapseAllBtn'),
    basicInfo: document.getElementById('basicInfo'),
    executionSummary: document.getElementById('executionSummary'),
    performanceSummary: document.getElementById('performanceSummary'),
    executionFlow: document.getElementById('executionFlow'),
    spansStats: document.getElementById('spansStats'),
    stepLogsStats: document.getElementById('stepLogsStats'),
    loadingOverlay: document.getElementById('loadingOverlay'),
    errorToast: document.getElementById('errorToast'),
    successToast: document.getElementById('successToast'),
    errorMessage: document.getElementById('errorMessage'),
    successMessage: document.getElementById('successMessage'),
    messageModal: document.getElementById('messageModal'),
    messageContent: document.getElementById('messageContent'),
    navigationList: document.getElementById('navigationList')
};

// Initialization
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Bind event listeners
    elements.browseDirectoryBtn.addEventListener('click', browseDirectory);
    elements.directoryInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            browseDirectory();
        }
    });
    elements.fileSelect.addEventListener('change', onFileSelect);
    elements.prevFileBtn.addEventListener('click', gotoPrevFile);
    elements.nextFileBtn.addEventListener('click', gotoNextFile);
    elements.loadBtn.addEventListener('click', loadTraceFile);
    elements.refreshBtn.addEventListener('click', refreshFileList);
    elements.expandAllBtn.addEventListener('click', expandAllSteps);
    elements.collapseAllBtn.addEventListener('click', collapseAllSteps);
    
    // Set default directory path
    setDefaultDirectory();
    
    // Initialize button state
    updateNavigationButtons();
    
    // Add keyboard shortcut support
    document.addEventListener('keydown', handleKeyboardShortcuts);
}

// Utility functions
function showLoading() {
    elements.loadingOverlay.classList.remove('d-none');
}

function hideLoading() {
    elements.loadingOverlay.classList.add('d-none');
}

function showError(message) {
    elements.errorMessage.textContent = message;
    const toast = new bootstrap.Toast(elements.errorToast);
    toast.show();
}

function showSuccess(message) {
    elements.successMessage.textContent = message;
    const toast = new bootstrap.Toast(elements.successToast);
    toast.show();
}

function formatTimestamp(timestamp) {
    if (!timestamp) return '';
    try {
        const date = new Date(timestamp);
        return date.toLocaleString('en-US');
    } catch (e) {
        return timestamp;
    }
}

function truncateText(text, maxLength = 100) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Handle MCP tool call display
function formatMcpToolCallWithPlaceholders(text, placeholders) {
    if (!text || typeof text !== 'string') return text;
    
    // MCP tool call regex - more lenient matching, including newlines
    const mcpPattern = /<use_mcp_tool>\s*<server_name>(.*?)<\/server_name>\s*<tool_name>(.*?)<\/tool_name>\s*<arguments>\s*(.*?)\s*<\/arguments>\s*<\/use_mcp_tool>/gs;
    
    let placeholderCounter = 0;
    
    return text.replace(mcpPattern, (match, serverName, toolName, args) => {
        // Clean and format parameters
        let formattedArgs = args.trim();
        
        // First convert escaped newlines to actual newlines
        formattedArgs = formattedArgs.replace(/\\n/g, '\n');
        
        try {
            // Try to format JSON parameters
            const parsed = JSON.parse(formattedArgs);
            formattedArgs = JSON.stringify(parsed, null, 2);
        } catch (e) {
            // If not JSON, keep as is but ensure newlines are correct
            formattedArgs = formattedArgs.replace(/\n/g, '\n');
        }
        
        const isBrowserAgent = serverName.trim() === 'browsing-agent';
        const toolClass = isBrowserAgent ? 'browser-agent' : '';
        const iconClass = isBrowserAgent ? 'globe' : 'cog';
        
        // Create complete MCP tool call HTML structure
        const mcpHtml = `<div class="mcp-tool-call ${toolClass}">
    <div class="mcp-tool-header">
        <i class="fas fa-${iconClass}"></i>
        <span class="mcp-tool-name">${serverName.trim()}.${toolName.trim()}</span>
    </div>
    <div class="mcp-tool-content">
        <div class="mcp-xml-structure">
            <div class="xml-tag">&lt;use_mcp_tool&gt;</div>
            <div class="xml-content">
                <div class="xml-tag">&lt;server_name&gt;${serverName.trim()}&lt;/server_name&gt;</div>
                <div class="xml-tag">&lt;tool_name&gt;${toolName.trim()}&lt;/tool_name&gt;</div>
                <div class="xml-tag">&lt;arguments&gt;</div>
                <div class="xml-arguments">${formattedArgs}</div>
                <div class="xml-tag">&lt;/arguments&gt;</div>
            </div>
            <div class="xml-tag">&lt;/use_mcp_tool&gt;</div>
        </div>
    </div>
</div>`;
        
        // Use simple placeholder ID to avoid complex JSON strings
        const placeholderId = `MCP_PLACEHOLDER_${placeholderCounter++}`;
        placeholders.set(placeholderId, mcpHtml);
        
        return `[${placeholderId}]`;
    });
}

// Create HTML for new format tool calls
function createNewFormatToolCallHTML(tool) {
    const isBeowserAgent = tool.server_name.includes('browsing') || tool.server_name.includes('agent');
    const toolClass = isBeowserAgent ? 'browser-agent' : '';
    const iconClass = isBeowserAgent ? 'globe' : 'cog';
    
    // Format parameters
    let formattedArgs;
    try {
        if (typeof tool.arguments === 'string') {
            formattedArgs = tool.arguments;
        } else {
            formattedArgs = JSON.stringify(tool.arguments, null, 2);
        }
    } catch (e) {
        formattedArgs = String(tool.arguments);
    }
    
    return `<div class="mcp-tool-call ${toolClass}">
    <div class="mcp-tool-header">
        <i class="fas fa-${iconClass}"></i>
        <span class="mcp-tool-name">${tool.server_name}.${tool.tool_name}</span>
        <span class="badge badge-format ms-2">${tool.format || 'new'}</span>
    </div>
    <div class="mcp-tool-content">
        <div class="mcp-tool-args">
            <div class="mcp-args-label">Parameters:</div>
            <div class="xml-arguments">${formattedArgs}</div>
        </div>
        ${tool.id ? `<div class="tool-id"><small class="text-muted">ID: ${tool.id}</small></div>` : ''}
    </div>
</div>`;
}

// Modified markdown rendering support - preserve markdown syntax, only handle line breaks and MCP tool calls
function renderMarkdown(text) {
    if (!text || typeof text !== 'string') return '';
    
    let html = text;
    let placeholders = new Map();
    
    // First handle MCP tool calls before HTML escaping
    html = formatMcpToolCallWithPlaceholders(html, placeholders);
    
    // Escape HTML special characters but protect MCP tool call placeholders
    html = html.replace(/&/g, '&amp;')
               .replace(/</g, '&lt;')
               .replace(/>/g, '&gt;')
               .replace(/"/g, '&quot;')
               .replace(/'/g, '&#39;');
    
    // Only handle line breaks, preserve all markdown syntax
    html = html.replace(/\n/g, '<br>');
    
    // Finally handle MCP tool call placeholders, insert HTML directly
    placeholders.forEach((htmlContent, placeholderId) => {
        html = html.replace(`[${placeholderId}]`, htmlContent);
    });
    
    return html;
}

// Enhanced content rendering function
function isJsonString(str) {
    try {
        const trimmed = str.trim();
        if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || 
            (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
            JSON.parse(trimmed);
            return true;
        }
        return false;
    } catch (e) {
        return false;
    }
}

function formatJsonContent(content) {
    try {
        const trimmed = content.trim();
        const parsed = JSON.parse(trimmed);
        const formatted = JSON.stringify(parsed, null, 4);
        return `<div class="code-block"><pre><code>${formatted}</code></pre></div>`;
    } catch (e) {
        return content;
    }
}

function renderContent(content, isBrowserAgent = false) {
    if (!content) return '';
    
    // Check if it's a pure JSON string
    if (isJsonString(content)) {
        return formatJsonContent(content);
    }
    
    // Render Markdown directly (already includes MCP tool call handling)
    let processedContent = renderMarkdown(content);
    
    // If it's browser agent, add special styling
    if (isBrowserAgent) {
        processedContent = `<div class="browser-agent-content">${processedContent}</div>`;
    }
    
    return processedContent;
}

// API call function
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

// File management
function setDefaultDirectory() {
    // Set default directory to parent directory
    elements.directoryInput.value = '../';
    // Automatically load file list
    refreshFileList();
}

async function browseDirectory() {
    const directory = elements.directoryInput.value.trim();
    if (!directory) {
        showError('Please enter directory path');
        return;
    }
    
    await refreshFileList(directory);
}

async function refreshFileList(directory = null) {
    try {
        const targetDirectory = directory || elements.directoryInput.value.trim();
        if (!targetDirectory) {
            elements.fileSelect.innerHTML = '<option value="">Please enter directory path first...</option>';
            currentFileList = [];
            currentFileIndex = -1;
            updateNavigationButtons();
            return;
        }
        
        showLoading();
        
        const url = `/api/list_files?directory=${encodeURIComponent(targetDirectory)}`;
        const data = await apiCall(url);
        
        elements.fileSelect.innerHTML = '<option value="">Select Trace file...</option>';
        
        if (data.files.length === 0) {
            elements.fileSelect.innerHTML = '<option value="">No JSON files in this directory</option>';
            currentFileList = [];
            currentFileIndex = -1;
            showSuccess(`No JSON files found in directory "${targetDirectory}"`);
            updateNavigationButtons();
            return;
        }
        
        // Save file list to global variable
        currentFileList = data.files;
        currentFileIndex = -1;
        
        data.files.forEach((file, index) => {
            const option = document.createElement('option');
            option.value = file.path;
            option.dataset.index = index;
            const fileSize = formatFileSize(file.size);
            const modifiedDate = new Date(file.modified * 1000).toLocaleString('en-US');
            option.textContent = `${file.name} (${fileSize}, ${modifiedDate})`;
            elements.fileSelect.appendChild(option);
        });
        
        showSuccess(`Found ${data.files.length} JSON files in directory "${targetDirectory}"`);
        updateNavigationButtons();
        
    } catch (error) {
        showError('Failed to get file list: ' + error.message);
        elements.fileSelect.innerHTML = '<option value="">Failed to get file list</option>';
        currentFileList = [];
        currentFileIndex = -1;
        updateNavigationButtons();
    } finally {
        hideLoading();
    }
}

// File switching functionality
function onFileSelect() {
    const selectedOption = elements.fileSelect.options[elements.fileSelect.selectedIndex];
    if (selectedOption && selectedOption.dataset.index !== undefined) {
        currentFileIndex = parseInt(selectedOption.dataset.index);
        updateNavigationButtons();
    }
}

function gotoPrevFile() {
    if (currentFileIndex > 0) {
        currentFileIndex--;
        selectFileByIndex(currentFileIndex);
        loadTraceFile();
    }
}

function gotoNextFile() {
    if (currentFileIndex < currentFileList.length - 1) {
        currentFileIndex++;
        selectFileByIndex(currentFileIndex);
        loadTraceFile();
    }
}

function selectFileByIndex(index) {
    if (index >= 0 && index < currentFileList.length) {
        elements.fileSelect.selectedIndex = index + 1; // +1 because first option is "Select Trace file..."
        currentFileIndex = index;
        updateNavigationButtons();
    }
}

function updateNavigationButtons() {
    const hasPrev = currentFileIndex > 0;
    const hasNext = currentFileIndex >= 0 && currentFileIndex < currentFileList.length - 1;
    
    elements.prevFileBtn.disabled = !hasPrev;
    elements.nextFileBtn.disabled = !hasNext;
    
    // Update button tooltip text
    if (currentFileIndex >= 0 && currentFileList.length > 0) {
        const prevFile = hasPrev ? currentFileList[currentFileIndex - 1] : null;
        const nextFile = hasNext ? currentFileList[currentFileIndex + 1] : null;
        
        elements.prevFileBtn.title = prevFile ? `Previous: ${prevFile.name}` : 'No previous file';
        elements.nextFileBtn.title = nextFile ? `Next: ${nextFile.name}` : 'No next file';
    } else {
        elements.prevFileBtn.title = 'Previous file';
        elements.nextFileBtn.title = 'Next file';
    }
}

// Keyboard shortcut handling
function handleKeyboardShortcuts(event) {
    // Only handle shortcuts when no input field is focused
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA' || event.target.tagName === 'SELECT') {
        return;
    }
    
    // Prevent triggering when modal is open
    if (elements.messageModal.classList.contains('show')) {
        return;
    }
    
    switch (event.key) {
        case 'ArrowLeft':
            event.preventDefault();
            if (!elements.prevFileBtn.disabled) {
                gotoPrevFile();
            }
            break;
        case 'ArrowRight':
            event.preventDefault();
            if (!elements.nextFileBtn.disabled) {
                gotoNextFile();
            }
            break;
        case 'Enter':
            event.preventDefault();
            if (elements.fileSelect.value) {
                loadTraceFile();
            }
            break;
        case 'r':
        case 'R':
            if (event.ctrlKey) {
                event.preventDefault();
                refreshFileList();
            }
            break;
    }
}

async function loadTraceFile() {
    const selectedFile = elements.fileSelect.value;
    if (!selectedFile) {
        showError('Please select a trace file');
        return;
    }
    
    showLoading();
    
    try {
        // Load file
        await apiCall('/api/load_trace', {
            method: 'POST',
            body: JSON.stringify({ file_path: selectedFile })
        });
        
        // Load all data in parallel
        const [basicInfo, executionSummary, performanceSummary, executionFlow, spansStats, stepLogsStats] = await Promise.all([
            apiCall('/api/basic_info'),
            apiCall('/api/execution_summary'),
            apiCall('/api/performance_summary'),
            apiCall('/api/execution_flow'),
            apiCall('/api/spans_summary'),
            apiCall('/api/step_logs_summary')
        ]);
        
        // Update interface
        updateBasicInfo(basicInfo);
        updateExecutionSummary(executionSummary);
        updatePerformanceSummary(performanceSummary);
        updateExecutionFlow(executionFlow);
        updateSpansStats(spansStats);
        updateStepLogsStats(stepLogsStats);
        
        // Display current file information
        const currentFile = currentFileList[currentFileIndex];
        if (currentFile) {
            showSuccess(`File loaded successfully: ${currentFile.name} (${currentFileIndex + 1}/${currentFileList.length})`);
        } else {
            showSuccess('File loaded successfully');
        }
        
    } catch (error) {
        showError('Failed to load file: ' + error.message);
    } finally {
        hideLoading();
    }
}

// Interface update functions
function updateBasicInfo(data) {
    currentBasicInfo = data;
    
    const finalAnswer = data.final_boxed_answer || 'No answer available';
    const groundTruth = data.ground_truth || 'No correct answer available';
    
    const html = `
        <div class="stat-item">
            <span class="stat-label">Task ID:</span>
            <span class="stat-value">${data.task_id || 'N/A'}</span>
        </div>
        <div class="answer-box final-answer">
            <div class="answer-label">Final Answer</div>
            <div class="answer-content">${finalAnswer}</div>
        </div>
        <div class="answer-box ground-truth">
            <div class="answer-label">Correct Answer</div>
            <div class="answer-content">${groundTruth}</div>
        </div>
        <div class="stat-item">
            <span class="stat-label">Judgment Result:</span>
            <span class="stat-value badge ${data.llm_as_judge_result === 'CORRECT' ? 'bg-success' : 'bg-danger'}">${data.llm_as_judge_result || 'N/A'}</span>
        </div>
    `;
    
    elements.basicInfo.innerHTML = html;
}

function updateExecutionSummary(data) {
    const html = `
        <div class="stat-item">
            <span class="stat-label">Total Steps:</span>
            <span class="stat-value">${data.total_steps}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Tool Calls:</span>
            <span class="stat-value">${data.total_tool_calls}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Browser Sessions:</span>
            <span class="stat-value">${data.browser_sessions_count}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">browsing-agent.search_and_browse:</span>
            <span class="stat-value">${data.tool_usage_distribution['browsing-agent.search_and_browse'] || 0}</span>
        </div>
    `;
    
    elements.executionSummary.innerHTML = html;
}

function updatePerformanceSummary(data) {
    if (!data || Object.keys(data).length === 0) {
        elements.performanceSummary.innerHTML = '<p class="text-muted">No performance data</p>';
        return;
    }
    
    const html = `
        <div class="stat-item">
            <span class="stat-label">Total Execution Time:</span>
            <span class="stat-value">${(data.total_wall_time || 0).toFixed(2)}s</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">browsing_agent:</span>
            <span class="stat-value">${data.primary_breakdown?.browsing_agent ? (data.primary_breakdown.browsing_agent.total || 0).toFixed(2) : 0}s</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">main_agent:</span>
            <span class="stat-value">${data.primary_breakdown?.main_agent ? (data.primary_breakdown.main_agent.total || 0).toFixed(2) : 0}s</span>
        </div>
    `;
    
    elements.performanceSummary.innerHTML = html;
}

function updateExecutionFlow(data) {
    currentFlowData = data;
    
    if (!data || data.length === 0) {
        elements.executionFlow.innerHTML = '<p class="text-muted">No execution flow data</p>';
        updateNavigationList([]);
        return;
    }
    
    // Ensure each step is an independent top-level element
    const stepsContainer = document.createElement('div');
    stepsContainer.className = 'execution-steps-container';
    
    data.forEach((step, index) => {
        const stepElement = document.createElement('div');
        stepElement.innerHTML = createStepHTML(step, index);
        stepsContainer.appendChild(stepElement.firstElementChild);
    });
    
    elements.executionFlow.innerHTML = '';
    elements.executionFlow.appendChild(stepsContainer);
    
    // Update navigation list
    updateNavigationList(data);
    
    // Bind event listeners
    bindStepEventListeners();
}

function createStepHTML(step, index) {
    const roleClass = step.role === 'user' ? 'user-message' : 
                     step.role === 'tool' ? 'tool-message' : 
                     step.role === 'system' ? 'system-message' : 
                     'assistant-message';
    const agentClass = step.agent.includes('browser') ? 'browser-agent' : '';
    
    // Render content
    const renderedPreview = renderContent(step.content_preview);
    const renderedFullContent = renderContent(step.full_content);
    
    return `
        <div class="execution-step fade-in" data-step-id="${step.step_id}" data-agent="${step.agent}" id="step-${index}">
            <div class="step-header ${roleClass} ${agentClass}" data-toggle="collapse" data-target="#step-content-${index}">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <span class="badge badge-role badge-${step.role}">${step.role}</span>
                        <span class="badge badge-browser ms-2">${step.agent}</span>
                        ${step.tool_calls.length > 0 ? `<span class="badge bg-warning text-dark ms-2">${step.tool_calls.length} Tool Calls</span>` : ''}
                        ${step.browser_session ? `<span class="badge bg-success ms-2">Browser Session</span>` : ''}
                    </div>
                    <div class="d-flex align-items-center">
                        <span class="timestamp me-2">${formatTimestamp(step.timestamp)}</span>
                        <span class="step-toggle">
                            <i class="fas fa-chevron-down"></i>
                        </span>
                    </div>
                </div>
                <div class="content-preview mt-2">
                    <div class="preview-text">
                        ${renderedPreview}
                    </div>
                </div>
            </div>
            
            <div class="step-content collapse" id="step-content-${index}">
                <div class="mb-3">
                    <h6>Full Content:</h6>
                    <div class="rendered-content">${renderedFullContent}</div>
                </div>
                
                ${step.tool_calls.length > 0 ? `
                    <div class="mb-3">
                        <h6>Tool Calls:</h6>
                        ${step.tool_calls.map(tool => createToolCallHTML(tool)).join('')}
                    </div>
                ` : ''}
                
                ${step.browser_flow && step.browser_flow.length > 0 ? `
                    <div class="mb-3">
                        <h6>Browser Session Flow:</h6>
                        <div class="browser-session">
                            <div class="browser-session-header">
                                <i class="fas fa-globe"></i> ${step.browser_session} (${step.browser_flow.length} steps)
                            </div>
                            ${step.browser_flow.map(browserStep => createBrowserStepHTML(browserStep, index)).join('')}
                        </div>
                    </div>
                ` : ''}
                
                <div class="d-flex justify-content-end">
                    <button class="btn btn-outline-primary btn-sm" onclick="showFullMessage(${step.step_id})">
                        <i class="fas fa-expand"></i> View Details
                    </button>
                </div>
            </div>
        </div>
    `;
}

function createToolCallHTML(tool) {
    // If it's new format tool call, use new rendering method
    if (tool.format === 'new') {
        return createNewFormatToolCallHTML(tool);
    }
    
    // Old format (MCP or others) use original rendering method
    const isBeowserAgent = tool.server_name === 'browsing-agent' || tool.server_name.includes('agent');
    const toolClass = isBeowserAgent ? 'browser-agent' : '';
    
    return `
        <div class="tool-call ${toolClass}">
            <div class="tool-call-header">
                <i class="fas fa-${isBeowserAgent ? 'globe' : 'wrench'}"></i>
                ${tool.server_name}.${tool.tool_name}
                <span class="badge badge-format ms-2">${tool.format || 'mcp'}</span>
            </div>
            <div class="tool-arguments">
                <strong>Parameters:</strong>
                <div class="code-block">${JSON.stringify(tool.arguments, null, 2)}</div>
            </div>
        </div>
    `;
}

function createBrowserStepHTML(step, parentIndex) {
    // Create unique ID for browser step
    const browserId = `browser-${parentIndex}-${step.step_id}`;
    
    // Check if content is truncated
    const isContentTruncated = step.full_content && step.content_preview.length < step.full_content.length;
    
    // Render content
    const renderedPreview = renderContent(step.content_preview);
    const renderedFullContent = renderContent(step.full_content);
    
    return `
        <div class="browser-step ${step.role}" id="browser-step-${parentIndex}-${step.step_id}">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <div>
                    <span class="badge badge-role badge-${step.role}">${step.role}</span>
                    ${step.tool_calls.length > 0 ? `<span class="badge bg-warning text-dark ms-2">${step.tool_calls.length} Tools</span>` : ''}
                </div>
                <span class="timestamp">${formatTimestamp(step.timestamp)}</span>
            </div>
            <div class="content-preview" id="browser-preview-${browserId}">
                <div class="preview-text">
                    ${renderedPreview}
                    ${isContentTruncated ? `
                        <span class="text-muted">...</span>
                        <button class="btn btn-link btn-sm p-0 ms-2 expand-preview-btn" onclick="toggleBrowserPreview('${browserId}', ${parentIndex}, ${step.step_id})" data-expanded="false">
                            <i class="fas fa-chevron-down"></i> Expand
                        </button>
                    ` : ''}
                </div>
            </div>
            ${step.tool_calls.length > 0 ? `
                <div class="mt-2">
                    <h7>Tool Calls:</h7>
                    ${step.tool_calls.map(tool => createToolCallHTML(tool)).join('')}
                </div>
            ` : ''}
        </div>
    `;
}

function updateSpansStats(data) {
    if (!data || Object.keys(data).length === 0) {
        elements.spansStats.innerHTML = '<p class="text-muted">No Spans data</p>';
        return;
    }
    
    const html = `
        <div class="stat-item">
            <span class="stat-label">Total Spans:</span>
            <span class="stat-value">${data.total_spans}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Total Duration:</span>
            <span class="stat-value">${(data.total_duration || 0).toFixed(2)}s</span>
        </div>
        <div class="mt-3">
            <h6>Agent Statistics:</h6>
            ${Object.entries(data.agent_stats || {}).map(([agent, stats]) => `
                <div class="mb-2">
                    <strong>${agent}:</strong>
                    <div class="stat-item">
                        <span class="stat-label">Count:</span>
                        <span class="stat-value">${stats.count}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Duration:</span>
                        <span class="stat-value">${(stats.total_duration || 0).toFixed(2)}s</span>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
    
    elements.spansStats.innerHTML = html;
}

function updateStepLogsStats(data) {
    if (!data || Object.keys(data).length === 0) {
        elements.stepLogsStats.innerHTML = '<p class="text-muted">No step logs data</p>';
        return;
    }
    
    const html = `
        <div class="stat-item">
            <span class="stat-label">Total Logs:</span>
            <span class="stat-value">${data.total_logs}</span>
        </div>
        <div class="mt-3">
            <h6>Status Distribution:</h6>
            ${Object.entries(data.status_distribution || {}).map(([status, count]) => `
                <div class="stat-item">
                    <span class="stat-label">${status}:</span>
                    <span class="stat-value">${count}</span>
                </div>
            `).join('')}
        </div>
        <div class="mt-3">
            <h6>Step Type Distribution:</h6>
            ${Object.entries(data.step_type_distribution || {}).map(([type, count]) => `
                <div class="stat-item">
                    <span class="stat-label">${type}:</span>
                    <span class="stat-value">${count}</span>
                </div>
            `).join('')}
        </div>
    `;
    
    elements.stepLogsStats.innerHTML = html;
}

// Event handling functions
function bindStepEventListeners() {
    // Step collapse/expand
    document.querySelectorAll('.step-header').forEach(header => {
        header.addEventListener('click', function() {
            const target = this.getAttribute('data-target');
            const content = document.querySelector(target);
            const icon = this.querySelector('.step-toggle i');
            
            if (content.classList.contains('show')) {
                content.classList.remove('show');
                icon.className = 'fas fa-chevron-down';
            } else {
                content.classList.add('show');
                icon.className = 'fas fa-chevron-up';
            }
        });
    });
}

function expandAllSteps() {
    // Expand main agent steps
    document.querySelectorAll('.step-content').forEach(content => {
        content.classList.add('show');
    });
    document.querySelectorAll('.step-toggle i').forEach(icon => {
        icon.className = 'fas fa-chevron-up';
    });
    
    // Expand browser agent preview content
    document.querySelectorAll('.expand-preview-btn').forEach(button => {
        const isExpanded = button.getAttribute('data-expanded') === 'true';
        if (!isExpanded) {
            button.click();
        }
    });
}

function collapseAllSteps() {
    // Collapse main agent steps
    document.querySelectorAll('.step-content').forEach(content => {
        content.classList.remove('show');
    });
    document.querySelectorAll('.step-toggle i').forEach(icon => {
        icon.className = 'fas fa-chevron-down';
    });
    
    // Collapse browser agent preview content
    document.querySelectorAll('.expand-preview-btn').forEach(button => {
        const isExpanded = button.getAttribute('data-expanded') === 'true';
        if (isExpanded) {
            button.click();
        }
    });
}

// Toggle content preview expand/collapse
// Toggle browser preview expand/collapse
function toggleBrowserPreview(browserId, parentIndex, browserStepId) {
    const previewElement = document.getElementById(`browser-preview-${browserId}`);
    const button = previewElement.querySelector('.expand-preview-btn');
    const isExpanded = button.getAttribute('data-expanded') === 'true';
    
    if (!currentFlowData) return;
    
    const parentStep = currentFlowData[parentIndex];
    if (!parentStep || !parentStep.browser_flow) return;
    
    const browserStep = parentStep.browser_flow.find(step => step.step_id === browserStepId);
    if (!browserStep) return;
    
    if (isExpanded) {
        // Collapse
        const renderedPreview = renderContent(browserStep.content_preview);
        previewElement.querySelector('.preview-text').innerHTML = `
            ${renderedPreview}
            <span class="text-muted">...</span>
            <button class="btn btn-link btn-sm p-0 ms-2 expand-preview-btn" onclick="toggleBrowserPreview('${browserId}', ${parentIndex}, ${browserStepId})" data-expanded="false">
                <i class="fas fa-chevron-down"></i> Expand
            </button>
        `;
    } else {
        // Expand
        const renderedFullContent = renderContent(browserStep.full_content);
        previewElement.querySelector('.preview-text').innerHTML = `
            ${renderedFullContent}
            <button class="btn btn-link btn-sm p-0 ms-2 expand-preview-btn" onclick="toggleBrowserPreview('${browserId}', ${parentIndex}, ${browserStepId})" data-expanded="true">
                <i class="fas fa-chevron-up"></i> Collapse
            </button>
        `;
    }
}

function showFullMessage(stepId) {
    if (!currentFlowData) return;
    
    const step = currentFlowData.find(s => s.step_id === stepId);
    if (!step) return;
    
    const renderedFullContent = renderContent(step.full_content);
    
    const modal = new bootstrap.Modal(elements.messageModal);
    elements.messageContent.innerHTML = `
        <div class="mb-3">
            <h6>Step Information:</h6>
            <div class="row">
                <div class="col-md-4"><strong>Step ID:</strong> ${step.step_id}</div>
                <div class="col-md-4"><strong>Agent:</strong> ${step.agent}</div>
                <div class="col-md-4"><strong>Role:</strong> ${step.role}</div>
            </div>
            <div class="row mt-2">
                <div class="col-md-6"><strong>Time:</strong> ${formatTimestamp(step.timestamp)}</div>
                <div class="col-md-6"><strong>Tool Calls:</strong> ${step.tool_calls.length}</div>
            </div>
        </div>
        
        <div class="mb-3">
            <h6>Full Content:</h6>
            <div class="rendered-content">${renderedFullContent}</div>
        </div>
        
        ${step.tool_calls.length > 0 ? `
            <div class="mb-3">
                <h6>Tool Call Details:</h6>
                ${step.tool_calls.map(tool => `
                    <div class="card mb-2">
                        <div class="card-body">
                            <h7 class="card-title">${tool.server_name}.${tool.tool_name}</h7>
                            <div class="code-block">${JSON.stringify(tool.arguments, null, 2)}</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        ` : ''}
        
        ${step.browser_flow && step.browser_flow.length > 0 ? `
            <div class="mb-3">
                <h6>Browser Session Details:</h6>
                <div class="accordion" id="browserAccordion">
                    ${step.browser_flow.map((browserStep, index) => {
                        const renderedBrowserContent = renderContent(browserStep.full_content);
                        return `
                            <div class="accordion-item">
                                <h2 class="accordion-header">
                                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#browserStep${index}">
                                        Browser Step ${index + 1}: ${browserStep.role}
                                        ${browserStep.tool_calls.length > 0 ? `(${browserStep.tool_calls.length} tool calls)` : ''}
                                    </button>
                                </h2>
                                <div id="browserStep${index}" class="accordion-collapse collapse">
                                    <div class="accordion-body">
                                        <div class="rendered-content">${renderedBrowserContent}</div>
                                        ${browserStep.tool_calls.length > 0 ? `
                                            <div class="mt-2">
                                                <strong>Tool Calls:</strong>
                                                ${browserStep.tool_calls.map(tool => `
                                                    <div class="small text-muted">
                                                        ${tool.server_name}.${tool.tool_name}
                                                    </div>
                                                `).join('')}
                                            </div>
                                        ` : ''}
                                    </div>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        ` : ''}
    `;
    
    modal.show();
} 

// ==================== Navigation Features ====================

function updateNavigationList(data) {
    if (!data || data.length === 0) {
        elements.navigationList.innerHTML = '<p class="text-muted p-3 mb-0">No steps available</p>';
        return;
    }
    
    const navigationHTML = data.map((step, index) => {
        const summary = truncateText(step.content_preview, 50);
        const toolsInfo = step.tool_calls.length > 0 ? ` (${step.tool_calls.length} tools)` : '';
        const browserInfo = step.browser_session ? ' [Browser]' : '';
        
        let html = `
            <div class="nav-item" data-step-index="${index}" onclick="scrollToStep(${index})">
                <div class="d-flex align-items-center">
                    <span class="step-number">${index + 1}</span>
                    <span class="step-role ${step.role}">${step.role}</span>
                    ${step.browser_flow && step.browser_flow.length > 0 ? `
                        <span class="browser-toggle" onclick="toggleBrowserNav(${index}, event)">
                            <i class="fas fa-chevron-down"></i>
                        </span>
                    ` : ''}
                </div>
                <div class="step-summary">${summary}${toolsInfo}${browserInfo}</div>
            </div>
        `;
        
        // Add browser sub-steps
        if (step.browser_flow && step.browser_flow.length > 0) {
            html += `
                <div class="browser-sub-steps" id="browser-nav-${index}">
                    ${step.browser_flow.map((browserStep, browserIndex) => {
                        const browserSummary = truncateText(browserStep.content_preview, 40);
                        const browserToolsInfo = browserStep.tool_calls.length > 0 ? ` (${browserStep.tool_calls.length} tools)` : '';
                        
                        return `
                            <div class="nav-item browser-sub-step" data-step-index="${index}" data-browser-step-id="${browserStep.step_id}" onclick="scrollToBrowserStep(${index}, ${browserStep.step_id})">
                                <div class="d-flex align-items-center">
                                    <span class="step-number">${index + 1}.${browserIndex + 1}</span>
                                    <span class="step-role ${browserStep.role}">${browserStep.role}</span>
                                </div>
                                <div class="step-summary">${browserSummary}${browserToolsInfo}</div>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        }
        
        return html;
    }).join('');
    
    elements.navigationList.innerHTML = navigationHTML;
}

function scrollToStep(stepIndex) {
    const stepElement = document.getElementById(`step-${stepIndex}`);
    if (stepElement) {
        stepElement.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
        
        // Update active navigation item
        updateActiveNavItem(stepIndex);
        
        // Auto-expand if step is collapsed
        const stepContent = document.getElementById(`step-content-${stepIndex}`);
        if (stepContent && !stepContent.classList.contains('show')) {
            const collapseInstance = new bootstrap.Collapse(stepContent, {
                toggle: false
            });
            collapseInstance.show();
        }
    }
}

function scrollToBrowserStep(parentIndex, browserStepId) {
    const browserStepElement = document.getElementById(`browser-step-${parentIndex}-${browserStepId}`);
    if (browserStepElement) {
        browserStepElement.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
        
        // Update active navigation item
        updateActiveNavItem(parentIndex, browserStepId);
        
        // Ensure parent step is expanded
        const stepContent = document.getElementById(`step-content-${parentIndex}`);
        if (stepContent && !stepContent.classList.contains('show')) {
            const collapseInstance = new bootstrap.Collapse(stepContent, {
                toggle: false
            });
            collapseInstance.show();
        }
    }
}

function toggleBrowserNav(stepIndex, event) {
    event.stopPropagation(); // Prevent event bubbling
    
    const browserNavElement = document.getElementById(`browser-nav-${stepIndex}`);
    const toggleIcon = event.target.closest('.browser-toggle').querySelector('i');
    
    if (browserNavElement.classList.contains('expanded')) {
        browserNavElement.classList.remove('expanded');
        toggleIcon.className = 'fas fa-chevron-down';
    } else {
        browserNavElement.classList.add('expanded');
        toggleIcon.className = 'fas fa-chevron-up';
    }
}

function updateActiveNavItem(activeIndex, browserStepId = null) {
    // Remove all active states
    const navItems = elements.navigationList.querySelectorAll('.nav-item');
    navItems.forEach(item => item.classList.remove('active'));
    
    if (browserStepId) {
        // Activate browser sub-step
        const browserNavItem = elements.navigationList.querySelector(`[data-step-index="${activeIndex}"][data-browser-step-id="${browserStepId}"]`);
        if (browserNavItem) {
            browserNavItem.classList.add('active');
        }
    } else {
        // Activate main step
        const activeItem = elements.navigationList.querySelector(`[data-step-index="${activeIndex}"]:not([data-browser-step-id])`);
        if (activeItem) {
            activeItem.classList.add('active');
        }
    }
}

// Listen to scroll events and auto-update navigation active state
let scrollTimeout;
function handleScroll() {
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(() => {
        if (!currentFlowData) return;
        
        const steps = document.querySelectorAll('.execution-step');
        const browserSteps = document.querySelectorAll('.browser-step');
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const windowHeight = window.innerHeight;
        
        let activeIndex = 0;
        let activeBrowserStepId = null;
        let minDistance = Infinity;
        
        // Check browser sub-steps
        browserSteps.forEach((browserStep) => {
            const rect = browserStep.getBoundingClientRect();
            const distance = Math.abs(rect.top - windowHeight / 3);
            
            if (distance < minDistance && rect.top < windowHeight * 0.7) {
                minDistance = distance;
                const id = browserStep.id;
                const matches = id.match(/browser-step-(\d+)-(\d+)/);
                if (matches) {
                    activeIndex = parseInt(matches[1]);
                    activeBrowserStepId = parseInt(matches[2]);
                }
            }
        });
        
        // If no active browser step found, check main steps
        if (!activeBrowserStepId) {
            steps.forEach((step, index) => {
                const rect = step.getBoundingClientRect();
                const distance = Math.abs(rect.top - windowHeight / 3);
                
                if (distance < minDistance && rect.top < windowHeight * 0.7) {
                    minDistance = distance;
                    activeIndex = index;
                    activeBrowserStepId = null;
                }
            });
        }
        
        updateActiveNavItem(activeIndex, activeBrowserStepId);
    }, 100);
}

// Bind scroll event
window.addEventListener('scroll', handleScroll);