import L from "leaflet";
import "leaflet-rotatedmarker";
import "leaflet/dist/leaflet.css";

export function calculateDistanceHaversine(location1, location2, radius) {

	radius = radius || 6371e3;

	// convert latitude and longitude to radians first
    const lat1 = Math.PI * location1.latitude / 180;
    const lat2 = Math.PI * location2.latitude / 180;
    const d_phi = lat2 - lat1;
    const d_lambda = Math.PI * (location2.longitude - location1.longitude) / 180;

    const a = Math.sin(d_phi / 2) * Math.sin(d_phi / 2) + Math.cos(lat1) * Math.cos(lat2) * Math.sin(d_lambda / 2) * Math.sin(d_lambda / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    // console.log('|| {} - {} ||= {}'.format(location2, location1, earth_radius * c))

    return radius * c;
}

export function breakSegments(data, byStatus, separationRadius, timeInterval) {

	separationRadius = separationRadius || [100, 10000]; // 10m, 10km
	timeInterval = timeInterval || [2 * 60 * 1000, 60 * 60 * 1000]; // 2 minutes, 1 hour
    byStatus = byStatus || false; // split by status as well?

    const segments = [];

    let currentSegment = [];
    let lastPosition = null;
    const n = data.length;
    for (let i = 0; i < n; i++) {

		// current position
        const currentPosition = data[i];

        // distance?
		if (lastPosition != null) {
            const distance = calculateDistanceHaversine(lastPosition.location, currentPosition.location);
            const interval = Math.abs(Date.parse(lastPosition.timestamp) - Date.parse(currentPosition.timestamp));
            let newStatus = false;
            if (byStatus && lastPosition.status != currentPosition.status) {
			    newStatus = true;
			    // will break segment, add current position first
                var newCurrentPosition = Object.assign({}, currentPosition);
                newCurrentPosition.status = lastPosition.status;
                currentSegment.push(newCurrentPosition);
            }
			if (newStatus ||
                distance > separationRadius[1] ||
                interval > timeInterval[1] ||
                (interval > timeInterval[0] && distance > separationRadius[0])) {
                // terminate current segment
                segments.push(currentSegment);
                currentSegment = [];
            }
		}

		// add position to segment
		currentSegment.push(currentPosition);

		// update lastPosition
		lastPosition = currentPosition;

	}

	// anything left?
	if (currentSegment.length > 0) {
        // terminate last segment
        segments.push(currentSegment);
    }

	return segments;

}

export function createMarker(call_or_update, icon) {

    // default marker
    icon = icon || L.icon({
        iconUrl: '/static/icons/flag/blue.svg',
        iconSize: [15, 30],
    });

    const location = call_or_update.location;
    return L.marker(
        [location.latitude, location.longitude],
        {icon: icon});

}

export function createSegmentLine(map, updates) {

	// Store data in an array
    const latlngs = [];
    updates.forEach(function(update) {

		// push location
        const loc = update.location;
        latlngs.push([loc.latitude, loc.longitude]);

    });

	// Add line to map
	console.log('Adding segment');
	return L.polyline(latlngs, {color: "red"});

}

// Interact with widget to add an ambulance route
export function addAmbulanceRoute(map, data, byStatus) {

    byStatus = byStatus || false;

    // paginated?
    if ('results' in data) {
        data = data.results
    }

    // short return
    if (data.length === 0)
        return;

    // break segments
    const segments = breakSegments(data, byStatus);

    // loop on segments
    const n = segments.length;
    let last_segment = null;
    for (let i = 0; i < n; i++) {

	    // grab segment
        const segment = segments[i];

        // initial point
        const initialPoint = segment[0];

        if (i === 0) {

            // add starting marker
            console.log("Adding initial '" + initialPoint.status + "' marker");
            createMarker(segment[0])
                .addTo(map.map)
                .bindPopup('<strong>' + ambulance_status[initialPoint.status] + '</strong>')
                .on('mouseover',
                    function () {
                        // open popup bubble
                        this.openPopup().on('mouseout',
                            function () {
                                this.closePopup();
                            });
                    });

        } else if (byStatus) { // && i > 0

            const status = initialPoint.status;
            const last_status = last_segment[last_segment.length - 1].status;
            console.log('status = ' + status + ', last_status = ' + last_status);
            if (last_status !== status) {
                // add status marker
                console.log("Adding '" + status + "' marker");
                createMarker(initialPoint)
                    .addTo(map.map)
                    .bindPopup('<strong>' + ambulance_status[status] + '</strong>')
                    .on('mouseover',
                        function () {
                            // open popup bubble
                            this.openPopup().on('mouseout',
                                function () {
                                    this.closePopup();
                                });
                        });
            }

        }

        // add segment to map
        createSegmentLine(map, segment)
            .addTo(map.map);

        // last segment?
        if (i === n - 1 && segment.length > 0) {
            // add ending marker
            const finalPoint = segment[segment.length - 1];
            console.log("Adding final '" + finalPoint.status + "' marker");
            createMarker(finalPoint)
                .addTo(map.map)
                .bindPopup('<strong>' + ambulance_status[finalPoint.status] + '</strong>')
                .on('mouseover',
                    function () {
                        // open popup bubble
                        this.openPopup().on('mouseout',
                            function () {
                                this.closePopup();
                            });
                    });
        }

        last_segment = segment;

    }

    // create route filter
    //createRouteFilter(segments);

    console.log('Centering map');
    map.center(data[0].location);

}

export function createRouteFilter(map, segments) {

    // Add the checkbox on the top right corner for filtering.
    const container = L.DomUtil.create('div', 'filter-options bg-light');

    //Generate HTML code for checkboxes for each of the statuses.
    let filterHtml = "";

    filterHtml += '<div class="border border-dark rounded px-1 pt-1 pb-0">';
    segments.forEach(function (segment, index) {

        const date = new Date(Date.parse(segment[0].timestamp));
        filterHtml += '<div class="checkbox">'
            + '<label><input class="chk" data-status="layer_' + index + '" type="checkbox" value="" checked >'
            + date.toLocaleString()
            + '</label>'
            + '</div>';

    });
    filterHtml += "</div>";

    // Append html code to container
    container.innerHTML = filterHtml;

    // Add the checkboxes.
    const customControl = L.Control.extend({

        options: {
            position: 'topright'
        },

        onAdd: function () {
            return container;
        }

    });
    map.map.addControl(new customControl());

    // Add listener to remove status layer when filter checkbox is clicked
    $('.chk').change(function () {

        // Which layer?
        const layer = map.getLayerPane(this.getAttribute('data-status'));

        if (this.checked) {
            layer.style.display = 'block';
        } else {
            layer.style.display = 'none';
        }

    });

};
