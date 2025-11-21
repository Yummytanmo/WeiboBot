import React from 'react';
import { Box, Typography, Paper } from '@mui/material';

const NODE_LIBRARY = {
    fetch: [
        { id: 'fetch_feed', label: 'Fetch Feed', icon: '📥', description: '获取微博feed' }
    ],
    analyze: [
        { id: 'summarize_trending', label: 'Summarize Trending', icon: '📊', description: '分析热点' },
        { id: 'decide_interactions', label: 'Decide Interactions', icon: '🤔', description: '决策互动' },
    ],
    generate: [
        { id: 'generate_schedule', label: 'Generate Schedule', icon: '📅', description: '生成计划' },
        { id: 'compose_post', label: 'Compose Post', icon: '✍️', description: '生成草稿' },
        { id: 'review_post', label: 'Review Post', icon: '👁️', description: '审查帖子' },
    ],
    execute: [
        { id: 'post_weibo', label: 'Post Weibo', icon: '🚀', description: '发布微博' },
        { id: 'execute_interactions', label: 'Execute Interactions', icon: '💬', description: '执行互动' },
    ],
};

const NodeLibrary = () => {
    const onDragStart = (event, node) => {
        event.dataTransfer.setData('application/reactflow', JSON.stringify(node));
        event.dataTransfer.effectAllowed = 'move';
    };

    return (
        <Box sx={{ width: 250, p: 2, bgcolor: 'background.paper', borderRight: 1, borderColor: 'divider', overflowY: 'auto' }}>
            <Typography variant="h6" gutterBottom>节点库</Typography>

            {Object.entries(NODE_LIBRARY).map(([category, nodes]) => (
                <Box key={category} sx={{ mb: 3 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', fontWeight: 'bold' }}>
                        {category}
                    </Typography>
                    {nodes.map((node) => (
                        <Paper
                            key={node.id}
                            draggable
                            onDragStart={(e) => onDragStart(e, node)}
                            sx={{
                                p: 1.5,
                                mt: 1,
                                cursor: 'grab',
                                '&:hover': { bgcolor: 'action.hover' },
                                '&:active': { cursor: 'grabbing' }
                            }}
                        >
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <span style={{ fontSize: '1.2em' }}>{node.icon}</span>
                                <Box>
                                    <Typography variant="body2" fontWeight="medium">{node.label}</Typography>
                                    <Typography variant="caption" color="text.secondary">{node.description}</Typography>
                                </Box>
                            </Box>
                        </Paper>
                    ))}
                </Box>
            ))}
        </Box>
    );
};

export default NodeLibrary;
