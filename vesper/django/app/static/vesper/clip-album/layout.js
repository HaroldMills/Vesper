import { ArrayUtils } from '/static/vesper/util/array-utils.js';


class _Layout {


	constructor(div, clipViews, settings) {
		this._div = div;
		this._clipViews = clipViews;
		this.settings = settings;
	}


	get div() {
		return this._div;
	}


    get clipViews() {
    	return this._clipViews;
    }


    get settings() {
    	return this._settings;
    }


    set settings(settings) {
    	this._settings = settings;
    	this._pagination = this._paginate();
    }


    _paginate() {
		throw new Error('_Layout._paginate not implemented');
    }


	get numPages() {
		let numPages = this._pagination.length;
		return numPages == 0 ? numPages : numPages - 1;
	}


    get pagination() {
    	return this._pagination;
    }


	getPageClipNumRange(pageNum) {
		this._checkPageNum(pageNum);
		const clipNums = this._pagination;
		return [clipNums[pageNum], clipNums[pageNum + 1]];
	}


	_checkPageNum(pageNum) {

		if (this.numPages === 0)
			throw new Error(
				`Page number ${pageNum} is out of range since view has ` +
				`no pages.`);

		else if (pageNum < 0 || pageNum >= this.numPages)
			throw new Error(
				`Page number ${pageNum} is outside of range ` +
				`[0, ${this.numPages - 1}].`);

	}


	getClipPageNum(clipNum) {
		this._checkClipNum(clipNum);
		return ArrayUtils.findLastLE(this._pagination, clipNum);
	}


	_checkClipNum(clipNum) {

		const numClips = this._clipViews.length;

		if (numClips === 0)
			throw new Error(
				`Clip number ${clipNum} is out of range since view has ` +
				`no clips.`);

		else if (clipNum < 0 || clipNum >= numClips)
			throw new Error(
				`Clip number ${clipNum} is outside of range ` +
				`[0, ${numClips - 1}].`);

	}


    layOutClipViews(pageNum) {
        throw new Error('_Layout.layOutClipViews not implemented');
    }


}


/*

Clip album layout settings by layout type:

    Uniform Nonresizing Clip Views

        page:
            size: clips

        clip_view:
            width: pixels
            height: pixels
            x_spacing: pixels
            y_spacing: pixels
            selection_outline_width: pixels
            duration: seconds


    Uniform Resizing Clip Views

        page:
            width: columns
            height: rows

        clip_view:
            x_spacing: percent of page width
            y_spacing: percent of page width
            selection_outline_width: pixels
            duration: seconds


    Nonuniform Nonresizing Clip Views

        page:
            size: clips

        clip_view:
            time_scale: pixels per second
            height: pixels
            x_spacing: pixels
            y_spacing: pixels
            selection_outline_width: pixels
            initial_padding: seconds
            final_padding: seconds


    Nonuniform Resizing Clip Views

        page:
            width: seconds
            height: rows

        clip_view:
            x_spacing: percent of page width
            y_spacing: percent of page width
            selection_outline_width: pixels
            initial_padding: seconds
            final_padding: seconds

*/


// /** Layout that displays uniform, nonresizing clip views. */
// class _UniformNonresizingClipViewsLayout { }


// /** Layout that displays uniform, resizing clip views. */
// class _UniformResizingClipViewsLayout { }


/* Layout that displays nonuniform, nonresizing clip views. */
export class NonuniformNonresizingLayout extends _Layout {


	/**
	 * Settings:
	 *
	 *     page:
     *         size: clips
     *
     *     clip_view:
     *         time_scale: pixels per second
     *         height: pixels
     *         x_spacing: pixels
     *         y_spacing: pixels
     *         selection_outline_width: pixels
     *         initial_padding: seconds
     *         final_padding: seconds
     */


	/**
	 * Assigns clips to pages.
	 */
	_paginate() {

		const numClips = this.clipViews.length;

		if (numClips === 0)
			return [];

		else {

			const pageSize = this.settings.page.size;
			const numPages = Math.ceil(numClips / pageSize);
			const pagination = new Array(numPages + 1);

			let startClipNum = 0;
			for (let i = 0; i < numPages; i++) {
				pagination[i] = startClipNum;
				startClipNum += Math.min(pageSize, numClips - startClipNum);
			}
			pagination[numPages] = startClipNum;

			return pagination;

		}

	}


	layOutClipViews(pageNum) {

		this._checkPageNum(pageNum);

		const clipsDiv = this.div;

		_removeChildren(clipsDiv);

		const cv = this.settings.clipView;

		const y_margin = cv.ySpacing / 2;
		const x_margin = cv.xSpacing / 2;
		const margin = y_margin + 'px ' + x_margin + 'px ';

		// Style page div. It is important to set values for pretty much
		// all of the flexbox properties here since we allow switching
		// between different layouts for the same page div.
		clipsDiv.style.display = 'flex';
		clipsDiv.style.flexDirection = 'row';
		clipsDiv.style.flexWrap = 'wrap';
		clipsDiv.style.flex = '1 1 auto';
		clipsDiv.style.justifyContent = 'center';
		clipsDiv.style.alignContent = 'flex-start';
		clipsDiv.style.alignItems = 'flex-start';
		clipsDiv.style.width = 'auto';
		clipsDiv.style.margin = margin;

		const [startNum, endNum] = this.getPageClipNumRange(pageNum);
		const height = cv.height + 'px';

		for (let i = startNum; i < endNum; i++) {

			const clipView = this.clipViews[i];
			const clipDiv = clipView.div;
			const width = clipView.duration * cv.timeScale + 'px';

			// Style clip div. It is important to set values for
			// pretty much all of the sizing properties here since
			// we reuse clip divs across layouts.
		    clipDiv.className = 'clip';
		    clipDiv.style.position = 'relative';
		    clipDiv.style.minWidth = width;
		    clipDiv.style.width = width;
		    clipDiv.style.height = height;
		    clipDiv.style.margin = margin;

			clipsDiv.appendChild(clipDiv);

		}

		this._renderClipViews(pageNum);

	}


	// TODO: Reconsider whether or not we need to lay out clip divs
	// and render their contents in separate stages. If we do retain
	// the two separate stages, document why.
	_renderClipViews(pageNum) {

		const [startNum, endNum] = this.getPageClipNumRange(pageNum);

		for (let i = startNum; i < endNum; i++)
			this.clipViews[i].render();

	}


	// TODO: It seems that this is never called. Should we delete it?
//	onResize(pageNum) {
//
//		console.log('NonresizingLayout.onResize');
//		this._checkPageNum(pageNum);
//
//		// For this layout type resizes are handled by the flexbox layout.
//
//	}


}


/** Layout that displays nonuniform, resizing clip views. */
export class NonuniformResizingLayout extends _Layout {


	/**
	 * Settings:
	 *
	 *     page:
     *         width: seconds
     *         height: rows
     *
     *     clip_view:
     *         x_spacing: percent of page width
     *         y_spacing: percent of page width
     *         selection_outline_width: pixels
     *         initial_padding: seconds
     *         final_padding: seconds
	 */


	/**
	 * Assigns clips to pages and rows.
	 */
	_paginate() {

		const pg = this.settings.page;
		const cv = this.settings.clipView;
		const clipViews = this.clipViews;

		const pages = [];

		if (clipViews.length > 0) {

			const xSpacing = cv.xSpacing;
			const maxRowWidth = 100. - xSpacing;
			const widthFactor = 100. / pg.width;

			let page = [0];
		    let rowWidth = widthFactor * clipViews[0].duration + xSpacing;

		    let i = 1;

			for ( ; i < clipViews.length; i++) {

				const width = widthFactor * clipViews[i].duration + xSpacing;

				if (rowWidth + width <= maxRowWidth) {
					// clip fits on current row

					rowWidth += width;

				} else {
					// clip will start new row

					// We always append the clip number to the current
					// page, even if the clip will start a new page, so
					// that we can obtain an end clip number for any row
					// i of a page, even the last row, as page[i + 1],
					// and the length of row i as page[i + 1] - page[i].
					page.push(i);

					if (page.length > pg.height) {
						// new row will be on new page

						pages.push(page);
						page = [i];

					}

					rowWidth = width;

				}

			}

			// Wrap up last page.
			page.push(i);
			pages.push(page);

		}

		this._pages = pages;

		if (pages.length == 0)
			return [];

		else {
			const pagination = pages.map(p => p[0]);
			const lastPage = pages[pages.length - 1];
			pagination.push(lastPage[lastPage.length - 1]);
			return pagination;
		}

	}


	layOutClipViews(pageNum) {

		this._checkPageNum(pageNum);

		const clipsDiv = this.div;

		_removeChildren(clipsDiv);

		const pg = this.settings.page;
		const cv = this.settings.clipView;

		const xMargin = _toCssPercent(cv.xSpacing / 2.);
		const yMargin = _toCssPercent(cv.ySpacing / 2.);

		// Style the page div. It is important to set values for pretty
		// much all of the flexbox properties here since we allow switching
		// between different layouts for the same page div.
		clipsDiv.style.display = 'flex';
		clipsDiv.style.flexDirection = 'column';
		clipsDiv.style.flexWrap = 'nowrap';
		clipsDiv.style.flex = '1 1 auto';
		clipsDiv.style.justifyContent = 'flex-start';
		clipsDiv.style.alignContent = 'stretch';
		clipsDiv.style.alignItems = 'stretch';
		clipsDiv.style.width = 'auto';
		
		// The "yMargin" in the following leaves some extra space for
        // clip labels when they are above or below the clip view divs.
        // A better approach might be to take the label location into
        // consideration when performing layout and put the clip view
        // div and the label in an additional parent div when the label
        // is either above or below the clip view div. Or perhaps we
        // should always use the parent div, but place the label on
        // top of (in the z-order sense) the clip view div when needed.
		clipsDiv.style.margin = yMargin + ' 0';

		const rowStartClipNums = this._pages[pageNum];
		const clipViews = this.clipViews;

		for (let i = 0; i < pg.height; i++) {

			// Create row div. We create a separate div for each row so
			// we can lay out clip views whose durations exceed the display
			// width in a special way. See below for details.
			const rowDiv = document.createElement('div');
			rowDiv.className = 'clip-row';
			rowDiv.style.display = 'flex';
			rowDiv.style.flexDirection = 'row';
			rowDiv.style.flex = '1 1 1px';
			rowDiv.style.justifyContent = 'center';
			rowDiv.style.margin = yMargin + ' 0';

			if (i < rowStartClipNums.length) {
				// row contains clips

				const startNum = rowStartClipNums[i];
				const endNum = rowStartClipNums[i + 1];
				const rowLength = endNum - startNum

				for (let j = startNum; j < endNum; j++) {

					const clipView = clipViews[j];

					const width = 100 * (clipView.duration / pg.width);

					if (rowLength === 1 && width > 100) {
						// row contains a single clip view and that clip view
						// is wider than the display

						// In this case we change the row div's justify-content
						// CSS property from center to flex-start so the clip
						// starts at the left edge of the display and the user
						// can scroll right to see the portion that doesn't
						// fit. If we leave the clip centered there will be
						// no way for the user to see the first part of it,
						// which will be off the left side of the display.
						rowDiv.style.justifyContent = 'flex-start';

					}

					// Style clip div. It is important to set values for
					// pretty much all of the sizing properties here since
					// we reuse clip divs across layouts.
					const clipDiv = clipView.div;
				    clipDiv.className = 'clip';
				    clipDiv.style.position = 'relative';
				    clipDiv.style.flex = '0 0 ' + _toCssPercent(width);
				    clipDiv.style.minWidth = 'auto';
				    clipDiv.style.width = 'auto';
				    clipDiv.style.height = 'auto';
				    clipDiv.style.margin = '0 ' + xMargin;

					rowDiv.appendChild(clipDiv);

					// The following is a first attempt at a clip div that
					// includes a label div above a view div. For some
					// reason the spectrogram canvas takes up the whole
					// clip div, even though its containing view div
					// does not, thus hiding the label div.
//					const clipDiv = document.createElement('div');
//                    clipDiv.style.backgroundColor = 'gray';
//                    clipDiv.style.display = 'flex';
//                    clipDiv.style.flexDirection = 'column';
//					
//                    const labelDiv = document.createElement('div');
//                    labelDiv.innerHTML = 'Bobo';
//                    labelDiv.style.textAlign = 'center';
//					labelDiv.style.flex = '1 1 auto';
//                    clipDiv.appendChild(labelDiv);
//					
//                    const viewDiv = clipView.div;
//                    viewDiv.className = 'clip';
//                    viewDiv.style.flex = '1 1 auto';
//                    clipDiv.appendChild(viewDiv);
//                    
//                    clipDiv.style.position = 'relative';
//                    clipDiv.style.flex = '0 0 ' + _toCssPercent(width);
//                    clipDiv.style.minWidth = 'auto';
//                    clipDiv.style.width = 'auto';
//                    clipDiv.style.height = 'auto';
//                    clipDiv.style.margin = '0 ' + xMargin;

                    rowDiv.appendChild(clipDiv);

				}

			}

			clipsDiv.appendChild(rowDiv);

		}

		this._renderClipViews(pageNum);

	}


	// TODO: Reconsider whether or not we need to lay out clip divs
	// and render their contents in separate stages. If we do retain
	// the two separate stages, document why.
	_renderClipViews(pageNum) {

		const [startNum, endNum] = this.getPageClipNumRange(pageNum);

		const clipViews = this.clipViews;
		for (let i = startNum; i < endNum; i++)
			clipViews[i].render();

	}


	// TODO: It seems that this is never called. Should we delete it?
//	onResize(pageNum) {
//		console.log('ResizingLayout.onResize');
//		this._checkPageNum(pageNum);
//		this._renderClipViews(pageNum);
//	}


}


function _removeChildren(div) {
    while (div.firstChild)
    	div.removeChild(div.firstChild);
}


function _toCssPercent(x) {
	return x.toFixed(2) + '%';
}



// TODO: Treat layout classes as extensions, and get their names from
// static class properties.
function _createLayoutClassesObject() {
    return {
        'Nonuniform Nonresizing Clip Views': NonuniformNonresizingLayout,
        'Nonuniform Resizing Clip Views': NonuniformResizingLayout
    };
}


const layoutClasses = _createLayoutClassesObject();


export const Layout = {
    'classes': _createLayoutClassesObject()
};
