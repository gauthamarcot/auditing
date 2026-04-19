const { createApp, ref, reactive, onMounted, onUnmounted } = Vue;

const API_BASE = "http://127.0.0.1:8001/api/documents";

createApp({
    setup() {
        const currentTab = ref("ingestion"); // dashboard, ingestion, queue
        
        // Multi-Tenant State
        const companies = ref([]);
        const activeCompanyId = ref(1);
        
        const fetchCompanies = async () => {
            try {
                const res = await axios.get(`${API_BASE.replace('/documents', '/analytics')}/companies`);
                companies.value = res.data;
                if (companies.value.length > 0 && !companies.value.find(c => c.id === activeCompanyId.value)) {
                    activeCompanyId.value = companies.value[0].id;
                }
            } catch (err) {
                console.error("Failed to fetch companies", err);
            }
        };

        const addCompany = async () => {
            const name = prompt("Enter new company name:");
            if (!name) return;
            try {
                const res = await axios.post(`${API_BASE.replace('/documents', '/analytics')}/companies`, { name });
                companies.value.push(res.data);
                activeCompanyId.value = res.data.id;
            } catch (err) {
                alert("Failed to add company.");
            }
        };
        
        // Multi-slot file tracking
        const selectedFiles = reactive({
            invoices: null,
            bank: null,
            tax: null
        });
        const currentActiveSlot = ref(null); // Tracks which slot triggered the file input
        
        const isUploading = ref(false);
        const pendingDocs = ref([]);
        const approvedDocs = ref([]);
        const auditLogs = ref([]);
        const fileInput = ref(null);
        
        // Analytics state
        const pnlData = ref(null);
        const costData = ref(null);
        const bsData = ref(null);
        const isSyncing = ref(false);
        let chartsInstance = [];

        // Ledger View state
        const ledgerData = ref([]);
        const expandedLedgers = ref([]);
        const ledgerFormulas = ref({});
        const ledgerFormulaResults = ref({});

        // Calculator state
        const calcInput = ref("");
        const calcHistory = ref([]);

        // Fetch pending documents
        const fetchPendingDocs = async () => {
            try {
                const res = await axios.get(`${API_BASE}/pending?company_id=${activeCompanyId.value}`);
                pendingDocs.value = res.data.map(doc => ({
                    ...doc,
                    selected_group: doc.suggested_group || 'Uncategorized'
                }));
            } catch (err) {
                console.error("Failed to fetch pending docs", err);
            }
        };

        // Fetch audit ledger
        const fetchAuditLogs = async () => {
            try {
                const res = await axios.get(`${API_BASE}/audit`);
                auditLogs.value = res.data;
            } catch (err) {
                console.error("Failed to fetch audit logs", err);
            }
        };

        // Polling
        let pollInterval;
        onMounted(() => {
            fetchCompanies();
            fetchPendingDocs();
            fetchAuditLogs();
            pollInterval = setInterval(() => {
                fetchPendingDocs();
                fetchAuditLogs();
            }, 5000);
        });

        onUnmounted(() => {
            clearInterval(pollInterval);
        });

        const triggerFileInput = (slotType) => {
            currentActiveSlot.value = slotType;
            if (fileInput.value) {
                fileInput.value.click();
            }
        };

        const handleFileSelect = (event) => {
            const files = event.target.files;
            if (files.length > 0 && currentActiveSlot.value) {
                selectedFiles[currentActiveSlot.value] = files[0];
            }
            // Reset the input so the same file can be selected again if needed
            event.target.value = '';
            currentActiveSlot.value = null;
        };

        const handleDrop = (event, slotType) => {
            const files = event.dataTransfer.files;
            if (files.length > 0) {
                selectedFiles[slotType] = files[0];
            }
        };

        const uploadDocument = async (slotType) => {
            const fileToUpload = selectedFiles[slotType];
            if (!fileToUpload) return;
            
            isUploading.value = true;

            const formData = new FormData();
            formData.append("file", fileToUpload);
            formData.append("maker_id", "maker_user_1");
            formData.append("doc_type", slotType); // Pass doc_type to backend for future routing logic
            formData.append("company_id", activeCompanyId.value);

            try {
                await axios.post(`${API_BASE}/upload`, formData, {
                    headers: {
                        'Content-Type': 'multipart/form-data'
                    }
                });
                alert(`Document successfully ingested into the ${slotType} engine!`);
                selectedFiles[slotType] = null; // reset just this slot
                fetchPendingDocs();
                fetchAuditLogs();
            } catch (err) {
                alert(`Failed to ingest ${slotType} document.`);
                console.error(err);
            } finally {
                isUploading.value = false;
            }
        };

        const approveDocument = async (id) => {
            const doc = pendingDocs.value.find(d => d.id === id);
            
            try {
                const formData = new FormData();
                formData.append("checker_id", "checker_user_1");
                formData.append("ledger_group", doc.selected_group);
                formData.append("company_id", activeCompanyId.value);
                
                await axios.post(`${API_BASE}/${id}/approve`, formData);
                approvedDocs.value.push(id);
                alert("Document Approved! Ready to sync to Tally.");
                fetchPendingDocs();
                fetchAuditLogs();
            } catch (err) {
                alert("Failed to approve document.");
                console.error(err);
            }
        };

        const pushToTally = async (id) => {
            try {
                const formData = new FormData();
                formData.append("user_id", "system_user");
                await axios.post(`${API_BASE}/${id}/sync-tally`, formData);
                alert("Successfully pushed to Tally Prime XML API!");
                fetchPendingDocs();
                fetchAuditLogs();
            } catch (err) {
                alert("Failed to sync to Tally.");
                console.error(err);
            }
        };

        const formatCurrency = (value) => value.toLocaleString('en-IN');

        const renderCharts = () => {
            chartsInstance.forEach(chart => chart.destroy());
            chartsInstance = [];

            if (!pnlData.value || !costData.value) return;

            Vue.nextTick(() => {
                const breakdownCtx = document.getElementById('costBreakdownChart');
                if (breakdownCtx) {
                    chartsInstance.push(new Chart(breakdownCtx, {
                        type: 'doughnut',
                        data: {
                            labels: ['Direct Expenses', 'Indirect Expenses'],
                            datasets: [{
                                data: [costData.value.direct_expenses, costData.value.indirect_expenses],
                                backgroundColor: ['#58a6ff', '#f85149'],
                                borderWidth: 0
                            }]
                        },
                        options: { color: '#e6edf3' }
                    }));
                }

                const marginCtx = document.getElementById('pnlMarginChart');
                if (marginCtx) {
                    chartsInstance.push(new Chart(marginCtx, {
                        type: 'bar',
                        data: {
                            labels: ['Revenue', 'Gross Profit', 'Net Profit'],
                            datasets: [{
                                label: 'Amount (₹)',
                                data: [pnlData.value.total_revenue, pnlData.value.gross_profit, pnlData.value.net_profit],
                                backgroundColor: ['#A371F7', '#2ea043', '#238636'],
                                borderWidth: 0
                            }]
                        },
                        options: { scales: { y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.1)' } } }, color: '#e6edf3' }
                    }));
                }

                // MoM Trends Chart
                if (pnlData.value.monthly_trends && Object.keys(pnlData.value.monthly_trends).length > 0) {
                    const momCtx = document.getElementById('momTrendsChart');
                    if (momCtx) {
                        const months = Object.keys(pnlData.value.monthly_trends).sort();
                        const revs = months.map(m => pnlData.value.monthly_trends[m].revenue);
                        const nps = months.map(m => pnlData.value.monthly_trends[m].net_profit);

                        chartsInstance.push(new Chart(momCtx, {
                            type: 'line',
                            data: {
                                labels: months,
                                datasets: [
                                    {
                                        label: 'Revenue',
                                        data: revs,
                                        borderColor: '#A371F7',
                                        tension: 0.3
                                    },
                                    {
                                        label: 'Net Profit',
                                        data: nps,
                                        borderColor: '#2ea043',
                                        tension: 0.3
                                    }
                                ]
                            },
                            options: { color: '#e6edf3', scales: { y: { grid: { color: 'rgba(255,255,255,0.1)' } }, x: { grid: { color: 'rgba(255,255,255,0.1)' } } } }
                        }));
                    }
                }
            });
        };

        const fetchAnalytics = async () => {
            try {
                const [pnlRes, costRes] = await Promise.all([
                    axios.get(`${API_BASE.replace('/documents', '/analytics')}/pnl-summary?company_id=${activeCompanyId.value}`),
                    axios.get(`${API_BASE.replace('/documents', '/analytics')}/cost-breakdown?company_id=${activeCompanyId.value}`)
                ]);
                pnlData.value = pnlRes.data;
                costData.value = costRes.data;
                renderCharts();
            } catch (err) {
                console.error("Failed to load analytics", err);
            }
        };

        const fetchBalanceSheet = async () => {
            try {
                const res = await axios.get(`${API_BASE.replace('/documents', '/analytics')}/balance-sheet?company_id=${activeCompanyId.value}`);
                bsData.value = res.data;
            } catch (err) {
                console.error("Failed to load balance sheet", err);
            }
        };

        const getLedgerGroup = (name) => {
            const ledger = ledgerData.value.find(l => l.name === name);
            return ledger ? ledger.group : 'Unknown';
        };

        const triggerTallyPull = async () => {
            isSyncing.value = true;
            try {
                await axios.post(`${API_BASE.replace('/documents', '/analytics')}/tally-pull?company_id=${activeCompanyId.value}`);
                fetchAnalytics();
                fetchLedgers(); // Refresh ledgers automatically
                alert("Successfully imported day book and trial balance from Tally.");
            } catch (err) {
                alert("Failed to pull from Tally API.");
            } finally {
                isSyncing.value = false;
            }
        };

        const fetchLedgers = async () => {
            try {
                const res = await axios.get(`${API_BASE.replace('/documents', '/analytics')}/ledgers?company_id=${activeCompanyId.value}`);
                ledgerData.value = res.data;
            } catch (err) {
                console.error("Failed to load ledgers", err);
            }
        };

        const toggleLedger = (id) => {
            if (expandedLedgers.value.includes(id)) {
                expandedLedgers.value = expandedLedgers.value.filter(lId => lId !== id);
            } else {
                expandedLedgers.value.push(id);
            }
        };
        
        const evaluateFormula = (ledgerId) => {
            try {
                let expression = ledgerFormulas.value[ledgerId];
                if (!expression) return;
                
                // Remove leading = if present
                if (expression.startsWith('=')) {
                    expression = expression.substring(1);
                }
                
                // Extremely unsafe in standard PROD, but works for local widget mock.
                // Replaces pure math functions without executing statements.
                const safeEval = new Function('return ' + expression);
                const result = safeEval();
                ledgerFormulaResults.value[ledgerId] = '= ₹' + formatCurrency(result);
            } catch (err) {
                ledgerFormulaResults.value[ledgerId] = 'Error in formula';
            }
        };

        const computeRunningBalance = (txns) => {
            let balance = 0;
            return txns.map(txn => {
                if (txn.type === 'Debit') {
                    // For typical expense/asset, debit increases natural balance. 
                    // To keep it simple, we just do Debt - Credit mapping.
                    balance += txn.amount;
                } else if (txn.type === 'Credit') {
                    balance -= txn.amount;
                }
                return {
                    ...txn,
                    balance: balance
                };
            });
        };

        const calculateLedgerTotal = (txns) => {
            return txns.reduce((sum, txn) => sum + txn.amount, 0);
        };
        
        // Calculator Functions
        const calcAppend = (val) => { calcInput.value += val; };
        const calcClear = () => { calcInput.value = ""; };
        const calcEvaluate = () => {
            try {
                const safeEval = new Function('return ' + calcInput.value);
                let res = safeEval();
                if (res % 1 !== 0) res = res.toFixed(2);
                
                // Add to tape history
                calcHistory.value.unshift(`${calcInput.value} = ${res}`);
                if (calcHistory.value.length > 20) {
                    calcHistory.value.pop();
                }
                
                calcInput.value = res.toString();
            } catch (err) {
                calcInput.value = "Error";
            }
        };

        const calcMacro = (type) => {
            if (!pnlData.value) {
                alert("Financials not loaded yet. Sync with Tally or go to Dashboard first.");
                return;
            }
            if (type === 'GP%') {
                const rev = pnlData.value.total_revenue || 1;
                const gp = pnlData.value.gross_profit || 0;
                const pct = ((gp / rev) * 100).toFixed(2);
                calcInput.value = pct.toString();
                calcHistory.value.unshift(`GP Margin = ${pct}%`);
            } else if (type === 'NP%') {
                const rev = pnlData.value.total_revenue || 1;
                const np = pnlData.value.net_profit || 0;
                const pct = ((np / rev) * 100).toFixed(2);
                calcInput.value = pct.toString();
                calcHistory.value.unshift(`NP Margin = ${pct}%`);
            }
        };

        const startTour = () => {
            const tour = introJs();
            tour.setOptions({
                steps: [
                    {
                        title: "Navigation",
                        element: '.sidebar-nav',
                        intro: "Welcome to Arc Auditing! This sidebar is your control center for navigating between different modules."
                    },
                    {
                        title: "Ingestion Hub",
                        element: '.upload-slots-grid',
                        intro: "This is the Ingestion Hub. Drop your invoices and tax documents here to have our AI extract key data.",
                        tabId: "ingestion"
                    },
                    {
                        title: "Validation Queue",
                        element: '.checker-view',
                        intro: "As a Checker, you will review highlighted exceptions and approve data before it hits the ledgers.",
                        tabId: "queue"
                    },
                    {
                        title: "Books & Ledgers",
                        element: '.ledger-view',
                        intro: "View raw journal entries mapped directly to ledger accounts.",
                        tabId: "ledger"
                    },
                    {
                        title: "Financial Statements",
                        element: '.statements-view',
                        intro: "Review production-ready formatted Profit & Loss sheets and balancing Balance Sheets.",
                        tabId: "statements"
                    },
                    {
                        title: "Analytics Dashboard",
                        element: '.analyst-view',
                        intro: "Pull live data from Tally to generate graphs and insights.",
                        tabId: "dashboard"
                    },
                    {
                        title: "Calculator & Audit Log",
                        element: '.tour-sidebar',
                        intro: "Use the quick calculator for spot-checking, and view immutable audit trails."
                    }
                ],
                showProgress: true,
                showBullets: true,
                disableInteraction: true
            });

            tour.onbeforechange(function() {
                return new Promise((resolve) => {
                    const step = this._introItems[this._currentStep];
                    if (step.tabId && currentTab.value !== step.tabId) {
                        currentTab.value = step.tabId;
                        // Wait for Vue to process DOM updates
                        Vue.nextTick(() => {
                            resolve();
                        });
                    } else {
                        resolve();
                    }
                });
            });

            tour.onexit(() => {
                currentTab.value = 'help';
            });

            // We need to wait a tick if we initiate while not rendered
            setTimeout(() => { tour.start(); }, 100);
        };
        
        // Watch for tab change to render charts if moving to dashboard
        Vue.watch(currentTab, (newTab) => {
            if (newTab === 'dashboard') {
                if (pnlData.value) renderCharts(); 
            }
            if (newTab === 'ledger') {
                fetchLedgers();
            }
            if (newTab === 'queue') {
                fetchPendingDocs(); // Ensure fresh company data whenever we look at queue
            }
            if (newTab === 'statements') {
                fetchAnalytics();
                fetchBalanceSheet();
                fetchLedgers(); // Needed for getLedgerGroup mappings
            }
        });

        // Watch activeCompanyId to instantly switch context
        Vue.watch(activeCompanyId, () => {
            // Re-fetch everything visible on the screen based on active tab
            if (currentTab.value === 'dashboard' || currentTab.value === 'statements') {
                fetchAnalytics();
                fetchBalanceSheet();
            }
            if (currentTab.value === 'ledger' || currentTab.value === 'statements') {
                fetchLedgers();
            }
            if (currentTab.value === 'queue') {
                fetchPendingDocs();
            }
            fetchAuditLogs();
        });

        // Initial Ledger fetch attempt
        onMounted(() => {
            fetchLedgers();
        });

        return {
            currentTab,
            selectedFiles,
            isUploading,
            pendingDocs,
            approvedDocs,
            auditLogs,
            triggerFileInput,
            handleFileSelect,
            handleDrop,
            uploadDocument,
            approveDocument,
            pushToTally,
            fileInput,
            pnlData,
            costData,
            isSyncing,
            triggerTallyPull,
            formatCurrency,
            ledgerData,
            expandedLedgers,
            fetchLedgers,
            toggleLedger,
            evaluateFormula,
            computeRunningBalance,
            calculateLedgerTotal,
            ledgerFormulas,
            ledgerFormulaResults,
            calcInput,
            calcHistory,
            calcAppend,
            calcClear,
            calcEvaluate,
            calcMacro,
            bsData,
            fetchBalanceSheet,
            getLedgerGroup,
            startTour,
            companies,
            activeCompanyId,
            addCompany
        };
    }
}).mount('#app');
