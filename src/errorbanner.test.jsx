import React from 'react';
import { screen, fireEvent } from '@testing-library/react';
import { renderWithStore } from './testUtils';
import ErrorBanner from './errorbanner';

const stateWith = extra => ({ smokerpi: { graphData: [], graphIndex: 0, ...extra } });

test('renders nothing when there is no error', () => {
  renderWithStore(<ErrorBanner />, { preloadedState: stateWith({}) });
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

test('shows the error message', () => {
  renderWithStore(<ErrorBanner />, {
    preloadedState: stateWith({ error: 'Error calling api: Failed to fetch' }),
  });
  expect(screen.getByRole('alert')).toHaveTextContent('Error calling api: Failed to fetch');
});

test('dismissing the banner clears the error from the store', () => {
  const { store } = renderWithStore(<ErrorBanner />, {
    preloadedState: stateWith({ error: 'Error calling api: boom' }),
  });

  fireEvent.click(screen.getByLabelText('Close alert'));

  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(store.getState().smokerpi.error).toBeUndefined();
});
