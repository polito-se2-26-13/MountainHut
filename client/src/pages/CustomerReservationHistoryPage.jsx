import { useEffect, useState } from 'react';
import { Alert, Button, DatePicker, InputNumber, Modal, Select } from 'antd';
import dayjs from 'dayjs';
import { Link, Navigate, useNavigate } from 'react-router';
import { apiRequest } from '../api/api.js';
import { useAuth } from '../auth/AuthContext.jsx';
import { useToast } from '../components/ToastProvider.jsx';
import RequirementsEditor, { requirementsBody, withIds } from '../components/RequirementsEditor.jsx';
import { formatSlotLabel, getSlotId, getSlotStart, isAtLeast, normalizeSlots } from '../utils/slots.js';

const CHANGE_WINDOW_MS = 48 * 60 * 60 * 1000;

function formatTables(tables) {
  return tables
    .map(table => `${table.table_number} (${table.assigned_seats} seat${table.assigned_seats === 1 ? '' : 's'})`)
    .join(', ');
}

// the latest service first, and on the same day the later time first
function newestFirst(a, b) {
  return `${b.date} ${b.start_time}`.localeCompare(`${a.date} ${a.start_time}`);
}

function slotPlaceholder(isLoading, availableSlots) {
  if (isLoading) return 'Loading service times…';
  if (availableSlots) return 'Select a time';
  return 'No open times for this date';
}

function CustomerReservationHistoryPage() {
  const { session } = useAuth();
  const [reservations, setReservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [target, setTarget] = useState(null);
  const [form, setForm] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [slots, setSlots] = useState([]);
  const [slotsDate, setSlotsDate] = useState('');
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const notify = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    if (!session?.isAuthenticated || session.userProfile.role !== 'Hiker') return undefined;
    let active = true;
    apiRequest('/reservations/user', {
      headers: { Authorization: `Bearer ${session.token}` },
    })
      .then(response => {
        if (active) setReservations(response.sort(newestFirst));
      })
      .catch(requestError => {
        if (active) notify(requestError.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [session, notify]);

  useEffect(() => {
    if (!target || !form?.date) return undefined;
    let active = true;
    apiRequest(`/slots?date=${encodeURIComponent(form.date)}`, {
      headers: { Authorization: `Bearer ${session.token}` },
    })
      .then(async response => {
        const candidates = normalizeSlots(response).filter(
          slot => getSlotId(slot) != null && isAtLeast(form.date, getSlotStart(slot), CHANGE_WINDOW_MS)
        );
        const checks = await Promise.all(
          candidates.map(async slot => {
            try {
              const availability = await apiRequest(
                `/slots/${encodeURIComponent(getSlotId(slot))}/availability`,
                {
                  headers: { Authorization: `Bearer ${session.token}` },
                }
              );
              // the booking's own slot stays on offer even when full: its seats are released by the change
              const offered =
                availability.status === 'OPEN' &&
                (availability.is_available || getSlotId(slot) === target.slot_id);
              return offered ? slot : null;
            } catch {
              return null;
            }
          })
        );
        if (active) {
          setSlots(
            checks.filter(Boolean).sort((a, b) => getSlotStart(a).localeCompare(getSlotStart(b)))
          );
          setSlotsDate(form.date);
        }
      })
      .catch(requestError => {
        if (active) setError(requestError.message);
      })
      .finally(() => {
        if (active) setSlotsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [target, form?.date, session]);

  if (!session?.isAuthenticated || session.userProfile.role !== 'Hiker')
    return <Navigate to="/login" replace />;

  const changeBody = form && {
    slot_id: Number(form.slot_id),
    party_size: Number(form.party_size),
    special_requirements: requirementsBody(form.requirements),
  };
  const dirty =
    Boolean(form?.slot_id) &&
    (changeBody.slot_id !== target.slot_id ||
      changeBody.party_size !== target.party_size ||
      JSON.stringify(changeBody.special_requirements) !==
        JSON.stringify(requirementsBody(target.special_requirements)));

  function beginChange(reservation) {
    setTarget(reservation);
    setModalOpen(true);
    setForm({
      date: reservation.date,
      slot_id: reservation.slot_id,
      party_size: reservation.party_size,
      requirements: withIds(reservation.special_requirements),
    });
    setSlots([]);
    setSlotsDate('');
    setSlotsLoading(true);
    setError('');
    setFieldErrors({});
  }

  function closeModal() {
    if (submitting) return;
    // target and form are cleared in afterClose, so antd can close the Modal and give the focus back
    setModalOpen(false);
  }

  function updateForm(updates) {
    setForm(current => ({ ...current, ...updates }));
    setError('');
    setFieldErrors({});
  }

  async function handleChangeSubmit(event) {
    event.preventDefault();
    // an Enter during the closing animation must not send the change again
    if (!modalOpen) return;
    const validationErrors = {};
    if (!Number.isInteger(changeBody.party_size) || changeBody.party_size < 1)
      validationErrors.party_size = 'Party size must be at least 1.';
    if (
      slotsDate !== form.date ||
      !slots.some(slot => getSlotId(slot) === changeBody.slot_id)
    ) {
      validationErrors.slot_id = 'Choose an open service time at least 48 hours from now.';
    }
    setFieldErrors(validationErrors);
    if (Object.keys(validationErrors).length) return;

    setSubmitting(true);
    setError('');
    try {
      const updated = await apiRequest(
        `/reservations/reference/${encodeURIComponent(target.booking_reference)}/change`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${session.token}` },
          body: JSON.stringify(changeBody),
        }
      );
      setReservations(list =>
        list
          .map(item => (item.id === updated.id ? updated : item))
          .sort(newestFirst)
      );
      closeModal();
      notify('Booking updated. A confirmation email is on its way.', 'success');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page reservation-history-page">
      <header className="reservation-history-header">
        <div>
          <button
            className="back-link"
            type="button"
            onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/home/hiker'))}
          >
            ← Back
          </button>
          <p className="eyebrow">MOUNTAINHUT · YOUR BOOKINGS</p>
          <h1>Booking history</h1>
          <p className="form-intro">Review your reservations and assigned seating.</p>
          <Link className="history-book-button" to="/customer/book-table">
            Book a table
          </Link>
        </div>
        <div className="booking-header-mark" aria-hidden="true">
          MH
        </div>
      </header>
      {loading && <p>Loading your bookings…</p>}
      {!loading && reservations.length === 0 && (
        <p className="reservation-history-empty">You don’t have any bookings yet.</p>
      )}
      {!loading && reservations.length > 0 && (
        <ul className="reservation-history-list">
          {reservations.map(reservation => {
            const confirmed = reservation.status === 'CONFIRMED';
            const canChange =
              confirmed && isAtLeast(reservation.date, reservation.start_time, CHANGE_WINDOW_MS);
            return (
              <li
                className={confirmed ? 'reservation-card-modifiable' : undefined}
                key={reservation.id}
              >
                <div className="reservation-card-details">
                  <strong>{reservation.booking_reference || 'Booking'}</strong>
                  {reservation.date && (
                    <span>
                      {reservation.date} · {reservation.start_time}–{reservation.end_time}
                    </span>
                  )}
                  <span>
                    {reservation.party_size ?? '—'} guest{reservation.party_size === 1 ? '' : 's'} ·{' '}
                    {reservation.status || 'Status unavailable'}
                  </span>
                  {reservation.assigned_tables?.length > 0 && (
                    <span>Tables: {formatTables(reservation.assigned_tables)}</span>
                  )}
                  {reservation.special_requirements?.length > 0 && (
                    <span>
                      Requests: {reservation.special_requirements.map(item => item.description).join(', ')}
                    </span>
                  )}
                  {(reservation.contact_name || reservation.contact_email) && (
                    <span>
                      Contact:{' '}
                      {[
                        reservation.contact_name,
                        reservation.contact_email,
                        reservation.contact_phone,
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </span>
                  )}
                </div>
                {confirmed && (
                  <div className="booking-change-action">
                    <Button
                      disabled={!canChange}
                      title={
                        !canChange
                          ? 'Changes are only permitted at least 48 hours in advance.'
                          : undefined
                      }
                      onClick={() => beginChange(reservation)}
                    >
                      Modify booking
                    </Button>
                    {!canChange && (
                      <small>Changes are only permitted at least 48 hours in advance.</small>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {target && form && (
        <Modal
          open={modalOpen}
          title="Modify booking"
          width={704}
          onCancel={closeModal}
          afterClose={() => {
            setTarget(null);
            setForm(null);
          }}
          footer={[
            <Button key="cancel" htmlType="button" onClick={closeModal} disabled={submitting}>
              Cancel
            </Button>,
            <Button
              key="save"
              type="primary"
              htmlType="submit"
              form="change-booking-form"
              loading={submitting}
              disabled={!dirty || slotsLoading}
            >
              Save changes
            </Button>,
          ]}
        >
          <div className="change-booking-summary">
            <span>
              <strong>Reference</strong>
              {target.booking_reference}
            </span>
            <span>
              <strong>Current tables</strong>
              {target.assigned_tables.length ? formatTables(target.assigned_tables) : 'Not assigned'}
            </span>
          </div>
          {error && (
            <Alert
              className="change-error-banner"
              type="error"
              showIcon
              title={error}
              description="Your original booking remains unchanged."
            />
          )}
          <form id="change-booking-form" className="change-modal-form mh-form" onSubmit={handleChangeSubmit}>
            <div className="change-fields">
              <label className="form-field">
                <span>
                  Date{' '}
                  <span className="required-mark" aria-hidden="true">
                    *
                  </span>
                </span>
                <DatePicker
                  className="mh-control"
                  format="YYYY-MM-DD"
                  value={form.date ? dayjs(form.date) : null}
                  disabledDate={date => date.isBefore(dayjs(), 'day')}
                  onChange={value => {
                    setSlots([]);
                    setSlotsDate('');
                    setSlotsLoading(true);
                    updateForm({ date: value?.format('YYYY-MM-DD') || '', slot_id: null });
                  }}
                  allowClear={false}
                />
              </label>
              <label className="form-field">
                <span>
                  Service time{' '}
                  <span className="required-mark" aria-hidden="true">
                    *
                  </span>
                </span>
                <Select
                  className="mh-control"
                  value={form.slot_id != null ? String(form.slot_id) : undefined}
                  loading={slotsLoading}
                  disabled={!form.date || slotsDate !== form.date || slots.length === 0}
                  placeholder={slotPlaceholder(slotsLoading, slots.length > 0)}
                  options={slots.map(slot => ({
                    value: String(getSlotId(slot)),
                    label: formatSlotLabel(slot),
                  }))}
                  onChange={value => updateForm({ slot_id: value })}
                />
                {fieldErrors.slot_id && (
                  <small className="field-error">{fieldErrors.slot_id}</small>
                )}
              </label>
              <label className="form-field party-size-field">
                <span>
                  Number of guests{' '}
                  <span className="required-mark" aria-hidden="true">
                    *
                  </span>
                </span>
                <InputNumber
                  className="mh-control"
                  min={1}
                  step={1}
                  precision={0}
                  value={form.party_size}
                  onChange={value => updateForm({ party_size: value ?? '' })}
                  aria-invalid={Boolean(fieldErrors.party_size)}
                />
                {fieldErrors.party_size && (
                  <small className="field-error">{fieldErrors.party_size}</small>
                )}
                <small className="field-hint change-capacity-hint">
                  Changing party size will release current seats and re-assign tables. If capacity
                  is insufficient, your original booking will remain unchanged.
                </small>
              </label>
              <div className="form-field requirements-field change-requirements-field">
                <div className="requirements-intro">
                  <span>
                    Special requirements <span className="optional-mark">(optional)</span>
                  </span>
                  <p>Share dietary needs or allergies for your group.</p>
                </div>
                <RequirementsEditor
                  requirements={form.requirements}
                  onChange={requirements => updateForm({ requirements })}
                />
              </div>
            </div>
          </form>
        </Modal>
      )}
    </main>
  );
}

export default CustomerReservationHistoryPage;
