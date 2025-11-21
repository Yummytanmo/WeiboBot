import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Box,
    Grid,
    Paper,
    Typography,
    List,
    ListItem,
    ListItemButton,
    ListItemText,
    Chip,
    Button,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    TextField,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    CircularProgress,
    IconButton,
} from '@mui/material';
import {
    Add as AddIcon,
    Refresh as RefreshIcon,
    Delete as DeleteIcon,
} from '@mui/icons-material';
import WorkflowGraphViewer from '../components/workflow/WorkflowGraphViewer';

const API_BASE = 'http://localhost:8000/api/workflow';

const WorkflowPage = () => {
    const [runs, setRuns] = useState([]);
    const [selectedRun, setSelectedRun] = useState(null);
    const [loading, setLoading] = useState(false);
    const [triggerModalOpen, setTriggerModalOpen] = useState(false);

    const [formData, setFormData] = useState({
        workflow: 'daily_schedule',
        agent_id: '7828522614',  // 默认账号ID
        llm_model: 'gpt-4o-mini',
        current_post_topic: '',
        max_review_rounds: 2,
        min_slots: 3,
        max_slots: 5,
    });

    useEffect(() => {
        fetchRuns();
        const interval = setInterval(fetchRuns, 3000);
        return () => clearInterval(interval);
    }, []);

    // 当选中的run状态改变时，自动更新
    useEffect(() => {
        if (selectedRun?.status === 'running') {
            const interval = setInterval(() => fetchRunDetails(selectedRun.id), 2000);
            return () => clearInterval(interval);
        }
    }, [selectedRun]);

    const fetchRuns = async () => {
        try {
            const res = await axios.get(`${API_BASE}/runs`);
            setRuns(res.data.runs || []);
        } catch (err) {
            console.error('Failed to fetch runs', err);
        }
    };

    const fetchRunDetails = async (runId) => {
        try {
            const res = await axios.get(`${API_BASE}/run/${runId}`);
            setSelectedRun(res.data);

            // 更新列表中的run
            setRuns(prev => prev.map(run =>
                run.id === runId ? { ...run, status: res.data.status } : run
            ));
        } catch (err) {
            console.error('Failed to fetch run details', err);
        }
    };

    const triggerWorkflow = async () => {
        setLoading(true);
        try {
            const res = await axios.post(`${API_BASE}/trigger`, formData);
            setTriggerModalOpen(false);
            fetchRuns();
            // 自动选中新创建的run
            setTimeout(() => fetchRunDetails(res.data.run_id), 500);
        } catch (err) {
            console.error('Failed to trigger workflow', err);
            alert('Failed to trigger workflow: ' + (err.response?.data?.detail || err.message));
        } finally {
            setLoading(false);
        }
    };

    const deleteRun = async (runId) => {
        try {
            await axios.delete(`${API_BASE}/run/${runId}`);
            setRuns(prev => prev.filter(run => run.id !== runId));
            if (selectedRun?.id === runId) {
                setSelectedRun(null);
            }
        } catch (err) {
            console.error('Failed to delete run', err);
        }
    };

    const getStatusColor = (status) => {
        const colors = {
            pending: 'default',
            running: 'primary',
            completed: 'success',
            failed: 'error',
        };
        return colors[status] || 'default';
    };

    return (
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h4">Workflows</Typography>
                <Box>
                    <Button
                        variant="outlined"
                        startIcon={<RefreshIcon />}
                        onClick={fetchRuns}
                        sx={{ mr: 1 }}
                    >
                        Refresh
                    </Button>
                    <Button
                        variant="contained"
                        startIcon={<AddIcon />}
                        onClick={() => setTriggerModalOpen(true)}
                    >
                        New Workflow
                    </Button>
                </Box>
            </Box>

            <Grid container spacing={2} sx={{ flexGrow: 1, overflow: 'hidden' }}>
                {/* 左侧：Workflow列表 */}
                <Grid item xs={12} md={4}>
                    <Paper sx={{ height: '100%', overflow: 'auto', p: 2 }}>
                        <Typography variant="h6" gutterBottom>Workflow Runs</Typography>
                        <List>
                            {runs.length === 0 && (
                                <ListItem>
                                    <ListItemText
                                        primary="No workflows yet"
                                        secondary="Click 'New Workflow' to start"
                                    />
                                </ListItem>
                            )}
                            {runs.map((run) => (
                                <ListItem
                                    key={run.id}
                                    disablePadding
                                    secondaryAction={
                                        <IconButton edge="end" onClick={() => deleteRun(run.id)}>
                                            <DeleteIcon />
                                        </IconButton>
                                    }
                                >
                                    <ListItemButton
                                        selected={selectedRun?.id === run.id}
                                        onClick={() => fetchRunDetails(run.id)}
                                    >
                                        <ListItemText
                                            primary={
                                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                    <Typography variant="body1">
                                                        {run.workflow.replace(/_/g, ' ')}
                                                    </Typography>
                                                    <Chip
                                                        label={run.status}
                                                        color={getStatusColor(run.status)}
                                                        size="small"
                                                    />
                                                </Box>
                                            }
                                            secondary={new Date(run.created_at).toLocaleString()}
                                        />
                                    </ListItemButton>
                                </ListItem>
                            ))}
                        </List>
                    </Paper>
                </Grid>

                {/* 右侧：详情和可视化 */}
                <Grid item xs={12} md={8}>
                    {!selectedRun ? (
                        <Paper sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', p: 4 }}>
                            <Typography variant="h6" color="text.secondary">
                                Select a workflow to view details
                            </Typography>
                        </Paper>
                    ) : (
                        <Paper sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                            {/* 头部信息 */}
                            <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                                    <Typography variant="h6">
                                        {selectedRun.workflow.replace(/_/g, ' ')}
                                    </Typography>
                                    <Chip label={selectedRun.status} color={getStatusColor(selectedRun.status)} />
                                </Box>
                                <Typography variant="caption" color="text.secondary">
                                    ID: {selectedRun.id}
                                </Typography>
                                {selectedRun.current_node && (
                                    <Typography variant="body2" color="primary" sx={{ mt: 1 }}>
                                        Current: {selectedRun.current_node}
                                    </Typography>
                                )}
                            </Box>

                            {/* 可视化图 */}
                            <Box sx={{ flexGrow: 1, minHeight: 300 }}>
                                <WorkflowGraphViewer
                                    workflowType={selectedRun.workflow}
                                    currentNode={selectedRun.current_node}
                                    nodeStatuses={selectedRun.nodes || []}
                                />
                            </Box>

                            {/* 日志和结果 */}
                            <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider', maxHeight: 200, overflow: 'auto' }}>
                                <Typography variant="subtitle2" gutterBottom>Logs</Typography>
                                <pre style={{ fontSize: '0.8em', margin: 0, whiteSpace: 'pre-wrap' }}>
                                    {selectedRun.logs || 'No logs yet...'}
                                </pre>
                                {selectedRun.error && (
                                    <Box sx={{ mt: 2, p: 1, bgcolor: 'error.light', borderRadius: 1 }}>
                                        <Typography variant="subtitle2" color="error.dark">Error:</Typography>
                                        <Typography variant="body2" color="error.dark">{selectedRun.error}</Typography>
                                    </Box>
                                )}
                            </Box>
                        </Paper>
                    )}
                </Grid>
            </Grid>

            {/* 触发Workflow对话框 */}
            <Dialog open={triggerModalOpen} onClose={() => !loading && setTriggerModalOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Trigger New Workflow</DialogTitle>
                <DialogContent>
                    <FormControl fullWidth sx={{ mt: 2 }}>
                        <InputLabel>Workflow Type</InputLabel>
                        <Select
                            value={formData.workflow}
                            onChange={(e) => setFormData({ ...formData, workflow: e.target.value })}
                            label="Workflow Type"
                        >
                            <MenuItem value="daily_schedule">Daily Schedule</MenuItem>
                            <MenuItem value="post_review">Post Review</MenuItem>
                            <MenuItem value="browse_interaction">Browse Interaction</MenuItem>
                            <MenuItem value="daily_agent">Daily Agent (Full)</MenuItem>
                        </Select>
                    </FormControl>


                    <FormControl fullWidth sx={{ mt: 2 }}>
                        <InputLabel>Agent ID</InputLabel>
                        <Select
                            value={formData.agent_id}
                            onChange={(e) => setFormData({ ...formData, agent_id: e.target.value })}
                            label="Agent ID"
                        >
                            <MenuItem value="7828522614">7828522614</MenuItem>
                        </Select>
                    </FormControl>


                    {(formData.workflow === 'post_review' || formData.workflow === 'daily_agent') && (
                        <TextField
                            fullWidth
                            label="Post Topic"
                            value={formData.current_post_topic}
                            onChange={(e) => setFormData({ ...formData, current_post_topic: e.target.value })}
                            sx={{ mt: 2 }}
                            placeholder="e.g., AI技术进展"
                        />
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setTriggerModalOpen(false)} disabled={loading}>
                        Cancel
                    </Button>
                    <Button
                        onClick={triggerWorkflow}
                        variant="contained"
                        disabled={loading || !formData.agent_id}
                    >
                        {loading ? <CircularProgress size={24} /> : 'Trigger'}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default WorkflowPage;
