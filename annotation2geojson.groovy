// TODO:: Define the path for exporting
def path = "/Users/kuangda/Developer/1-projects/hubmap/st-analysis/annotations/QuPath-Projects/annotation-export/Visium_13_44_S1.geojson"
// Get the current image data
def imageData = getCurrentImageData()

// Extract image dimensions
def server = imageData.getServer()
def width = server.getWidth()
def height = server.getHeight()

// Print the image dimensions
print 'Image width: ' + width
print 'Image height: ' + height

// Get all annotations
def annotations = getAnnotationObjects()

// Specify the names of the annotations you want to export
def annotationNames = ['antimesosalpingx epithelium', 'antimesosalpingx muscularus', 'mesosalpingx epithelium', 'mesosalpingx muscularus'] // Replace with your desired names
//def annotationNames = ['antimesosalpingx muscularus', 'mesosalpingx muscularus'] // Replace with your desired names
// Define a map of annotation names to unique values (1, 2, 3, 4 for each channel)
def annotationValues = [
    'antimesosalpinx epithelium' : 1, 
    'antimesosalpinx muscularus' : 2, 
    'mesosalpinx epithelium'     : 3, 
    'mesosalpinx muscularus'     : 4
]

// Filter annotations by name and add unique values as measurements
def filteredAnnotations = annotations.findAll { annotation ->
    def name = annotation.getPathClass().toString()  // Assuming names are stored in the PathClass of the annotation
    return annotationNames.contains(name)
}

if (!filteredAnnotations.isEmpty()) {
    println "- Filtered Annotations:"
    filteredAnnotations.each { annotation ->
        def name = annotation.getPathClass().toString()

        // Assign a unique value to each annotation as a measurement
        def value = annotationValues.get(name)
        annotation.getMeasurementList().putMeasurement('Value', value)  // Assign a unique value as a measurement

        // Print the annotation name and its assigned value
        println "-- Annotation Name: ${name} assigned value: ${value}"
    }
} else {
    println "No annotations matched the specified names."
}

// Export the filtered annotations as GeoJSON
if (!filteredAnnotations.isEmpty()) {
    exportObjectsToGeoJson(filteredAnnotations, path, "FEATURE_COLLECTION")
    println "Annotations exported to: ${path}"
} else {
    println "No annotations matched the specified names, no export performed."
}
