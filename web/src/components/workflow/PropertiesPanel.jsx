import React from 'react';
import { Box, Typography, TextField, Divider } from '@mui/material';

const PropertiesPanel = ({ node }) => {
    if (!node) {
        return (
            <Box sx={{ width: 300, p: 2, bgcolor: 'background.paper', borderLeft: 1, borderColor: 'divider' }}>
                <Typography color="text.secondary" variant="body2">
                    选择一个节点以查看属性
                </Typography>
            </Box>
        );
    }

    return (
        <Box sx={{ width: 300, p: 2, bgcolor: 'background.paper', borderLeft: 1, borderColor: 'divider' }}>
            <Typography variant="h6" gutterBottom>属性</Typography>

            <Divider sx={{ my: 2 }} />

            <TextField
                label="节点ID"
                value={node.id}
                disabled
                fullWidth
                size="small"
                sx={{ mb: 2 }}
            />

            <TextField
                label="节点类型"
                value={node.data.id}
                disabled
                fullWidth
                size="small"
                sx={{ mb: 2 }}
            />

            <TextField
                label="标签"
                value={node.data.label}
                fullWidth
                size="small"
                sx={{ mb: 2 }}
            />

            <Typography variant="caption" color="text.secondary">
                {node.data.description}
            </Typography>
        </Box>
    );
};

export default PropertiesPanel;
