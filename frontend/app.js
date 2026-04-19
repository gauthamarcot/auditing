const { createApp, ref, onMounted, onUnmounted } = Vue;

// Change port below if your FastAPI dev server runs differently (e.g. 8000)
const API_BASE = "http://127.0.0.1:8000/api/documents";

createApp({
    setup() {
        const currentRole = ref("maker");
        const selectedFile = ref(null);
        const isUploading = ref(false);
        const pendingDocs = ref([]);
        const approvedDocs = ref([]);
        const auditLogs = ref([]);
        const fileInput = ref(null);
        
        // Analytics state
        const pnlData = ref(null);
        const costData = ref(null);
        const isSyncing = ref(false);
        let chartsInstance = [];

        // Fetch pending documents
        const fetchPendingDocs = async () => {
            try {
                const res = await axios.get(`${API_BASE}/pending`);
                pendingDocs.value = res.data;
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

        // Call both APIs frequently to simulate real-time updates for demo purposes
        let pollInterval;
        onMounted(() => {
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

        const triggerFileInput = () => {
            if (fileInput.value) {
                fileInput.value.click();
            }
        };

        const handleFileSelect = (event) => {
            const files = event.target.files;
            if (files.length > 0) {
                selectedFile.value = files[0];
            }
        };

        const handleDrop = (event) => {
            const files = event.dataTransfer.files;
            if (files.length > 0) {
                selectedFile.value = files[0];
            }
        };

        const uploadDocument = async () => {
            if (!selectedFile.value) return;
            isUploading.value = true;

            const formData = new FormData();
            formData.append("file", selectedFile.value);
            formData.append("maker_id", "maker_user_1");

            try {
                await axios.post(`${API_BASE}/upload`, formData, {
                    headers: {
                        'Content-Type': 'multipart/form-data'
                    }
                });
                alert("Document uploaded and AI extraction triggered successfully!");
                selectedFile.value = null; // reset
                fetchPendingDocs();
                fetchAuditLogs();
            } catch (err) {
                alert("Failed to upload document.");
                console.error(err);
            } finally {
                isUploading.value = false;
            }
        };

        const approveDocument = async (id) => {
            try {
                const formData = new FormData();
                formData.append("checker_id", "checker_user_1");
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
                alert("Failed to sync to Tally. Check if local server is running mock.");
                console.error(err);
            }
        };

        const formatCurrency = (value) => value.toLocaleString('en-IN');

        const renderCharts = () => {
            // Destroy old charts to prevent overlap
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
            });
        };

        const fetchAnalytics = async () => {
            try {
                const [pnlRes, costRes] = await Promise.all([
                    axios.get(`${API_BASE.replace('/documents', '/analytics')}/pnl-summary`),
                    axios.get(`${API_BASE.replace('/documents', '/analytics')}/cost-breakdown`)
                ]);
                pnlData.value = pnlRes.data;
                costData.value = costRes.data;
                renderCharts();
            } catch (err) {
                console.error("Failed to load analytics", err);
            }
        };

        const triggerTallyPull = async () => {
            isSyncing.value = true;
            try {
                await axios.post(`${API_BASE.replace('/documents', '/analytics')}/tally-pull`);
                fetchAnalytics();
                alert("Successfully imported day book and trial balance from Tally.");
            } catch (err) {
                alert("Failed to pull from Tally API.");
            } finally {
                isSyncing.value = false;
            }
        };
        
        // Watch for role change
        Vue.watch(currentRole, (newRole) => {
            if (newRole === 'analyst') {
                if (pnlData.value) renderCharts(); // re-render if switching back
            }
        });

        return {
            currentRole,
            selectedFile,
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
            // New Analytics state/functions
            pnlData,
            costData,
            isSyncing,
            triggerTallyPull,
            formatCurrency
        };
    }
}).mount('#app');
