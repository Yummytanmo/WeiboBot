import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
    Box,
    Drawer,
    AppBar,
    Toolbar,
    List,
    Typography,
    Divider,
    ListItem,
    ListItemButton,
    ListItemIcon,
    ListItemText,
    CssBaseline,
    ThemeProvider,
    createTheme
} from '@mui/material';
import {
    Chat as ChatIcon,
    AccountTree as WorkflowIcon,
    Dashboard as DashboardIcon
} from '@mui/icons-material';

const drawerWidth = 240;

const darkTheme = createTheme({
    palette: {
        mode: 'dark',
        primary: {
            main: '#90caf9',
        },
        secondary: {
            main: '#f48fb1',
        },
        background: {
            default: '#121212',
            paper: '#1e1e1e',
        },
    },
});

const Layout = ({ children }) => {
    const location = useLocation();

    const menuItems = [
        { text: 'Agent Chat', icon: <ChatIcon />, path: '/agent' },
        { text: 'Workflows', icon: <WorkflowIcon />, path: '/workflow' },
    ];

    return (
        <ThemeProvider theme={darkTheme}>
            <CssBaseline />
            <Box sx={{ display: 'flex' }}>
                <AppBar
                    position="fixed"
                    sx={{ width: `calc(100% - ${drawerWidth}px)`, ml: `${drawerWidth}px` }}
                >
                    <Toolbar>
                        <Typography variant="h6" noWrap component="div">
                            WeiboBot Console
                        </Typography>
                    </Toolbar>
                </AppBar>
                <Drawer
                    sx={{
                        width: drawerWidth,
                        flexShrink: 0,
                        '& .MuiDrawer-paper': {
                            width: drawerWidth,
                            boxSizing: 'border-box',
                        },
                    }}
                    variant="permanent"
                    anchor="left"
                >
                    <Toolbar>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                            <DashboardIcon color="primary" />
                            <Typography variant="h6" color="primary" sx={{ fontWeight: 'bold' }}>
                                WeiboBot
                            </Typography>
                        </Box>
                    </Toolbar>
                    <Divider />
                    <List>
                        {menuItems.map((item) => (
                            <ListItem key={item.text} disablePadding>
                                <ListItemButton
                                    component={Link}
                                    to={item.path}
                                    selected={location.pathname.startsWith(item.path)}
                                >
                                    <ListItemIcon>
                                        {item.icon}
                                    </ListItemIcon>
                                    <ListItemText primary={item.text} />
                                </ListItemButton>
                            </ListItem>
                        ))}
                    </List>
                </Drawer>
                <Box
                    component="main"
                    sx={{ flexGrow: 1, bgcolor: 'background.default', p: 3, height: '100vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
                >
                    <Toolbar />
                    <Box sx={{ flexGrow: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                        {children}
                    </Box>
                </Box>
            </Box>
        </ThemeProvider>
    );
};

export default Layout;
